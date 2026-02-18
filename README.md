# resolve-container-image

Resolve a container image from explicit input, terraform state, or release branch. Prevents accidental image rollbacks during infra-only terraform applies.

## The problem

You have EKS services deployed via Terraform. You need to change an IAM policy. You run `terraform apply`. Your IAM policy updates — and your container images silently roll back to whatever default was hardcoded in `variables.tf` three months ago.

## The solution

A priority chain that asks: what does the operator actually intend?

```
explicit_image? ──yes──> parse and use
       │
       no
       │
       ▼
state has image? ──yes──> extract and use
       │
       no
       │
       ▼
resolve from release branch
```

**`update_images`** (default: `false`) is the safety gate. When false, state wins — infra changes are infra-only. When true, skip state and resolve latest images from the release branch.

## Usage

```yaml
- name: Resolve API image
  id: api-image
  uses: fizz/resolve-container-image@v1
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  with:
    registry_prefix: '123456789012.dkr.ecr.us-east-1.amazonaws.com'
    image_repo: myapp-api
    github_repo: myapp
    github_org: my-org
    update_images: ${{ inputs.update_images || 'false' }}
    terraform_resource_address: module.api.kubernetes_deployment_v1.service
    terraform_working_dir: terraform/services/api

- name: Terraform Apply
  run: |
    terraform apply -auto-approve \
      -var="api_image=${{ steps.api-image.outputs.repository }}" \
      -var="api_tag=${{ steps.api-image.outputs.tag }}" \
      -var="api_digest=${{ steps.api-image.outputs.digest }}"
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `registry` | no | `ecr` | Container registry type |
| `registry_prefix` | **yes** | | Registry URL prefix |
| `image_repo` | **yes** | | Image repository name |
| `github_repo` | **yes** | | GitHub repo for release branch discovery |
| `github_org` | **yes** | | GitHub org/user |
| `explicit_image` | no | `""` | Override: `repo:tag` or `repo:tag@sha256:digest` |
| `update_images` | no | `"false"` | Skip state, resolve from release branch |
| `release_branch` | no | `""` | Explicit branch; blank = latest `releases/*` |
| `terraform_resource_address` | no | `""` | Resource address for state read |
| `terraform_working_dir` | no | `""` | Working dir for `terraform show` |

## Outputs

| Output | Description |
|--------|-------------|
| `repository` | Image repository URL |
| `tag` | Image tag |
| `digest` | Image digest (`sha256:...`) |
| `full_image` | Full reference (`repo:tag@digest`) |
| `source` | Resolution source: `explicit`, `state`, or `release_branch` |

## Scenarios

| Operation | `update_images` | Image source | Result |
|-----------|----------------|--------------|--------|
| IAM policy change | `false` (default) | state | IAM updates, images untouched |
| Deploy new release | `true` | release branch | Latest images deployed |
| New service (no state) | `false` (default) | release branch | Gets latest images |
| Hotfix specific image | n/a | explicit | Exact image deployed |

## Prerequisites

- AWS credentials configured (for ECR digest resolution)
- Terraform initialized in `terraform_working_dir` (for state reads)
- `GH_TOKEN` with repo read access (for release branch discovery)

## How it works

**State reading:** `terraform show -json` dumps state as JSON. A jq query extracts the container image from the Kubernetes deployment spec at the given resource address.

**Digest pinning:** Tags are mutable — someone can push a new image to the same tag. This action always resolves and pins the sha256 digest, whether the image came from state, release branch, or explicit input.

**Error handling:** ECR digest resolution uses [aws-error-utils](https://github.com/benkehoe/aws-error-utils) for specific exception handling. `ImageNotFoundException`, `RepositoryNotFoundException`, and `AccessDeniedException` each produce distinct error messages instead of generic failures.

## Registry support

Currently supports AWS ECR. The pattern generalizes to any OCI registry — the only registry-specific code is `ecr_resolve.py`. PRs welcome for GHCR, GAR, Docker Hub.

## License

MIT
