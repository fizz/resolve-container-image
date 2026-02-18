#!/usr/bin/env python3
"""Resolve ECR image digest with proper error handling.

Usage:
    ecr_resolve.py <repo_name> <tag>

Prints digest (sha256:...) to stdout on success.
Exits non-zero with specific codes on failure:
    1 - image not found (tag doesn't exist in repo)
    2 - repository not found
    3 - auth/permissions error
    4 - unexpected error
"""
import sys

import boto3
from aws_error_utils import catch_aws_error


def resolve_digest(repo_name: str, tag: str) -> str:
    ecr = boto3.client("ecr")
    try:
        resp = ecr.describe_images(
            repositoryName=repo_name,
            imageIds=[{"imageTag": tag}],
        )
        details = resp.get("imageDetails", [])
        if not details:
            print(f"::error::No image details returned for {repo_name}:{tag}", file=sys.stderr)
            sys.exit(1)
        return details[0]["imageDigest"]

    except catch_aws_error("ImageNotFoundException"):
        print(f"::error::Image {repo_name}:{tag} not found — tag may have been deleted or never built", file=sys.stderr)
        sys.exit(1)

    except catch_aws_error("RepositoryNotFoundException"):
        print(f"::error::ECR repository '{repo_name}' does not exist", file=sys.stderr)
        sys.exit(2)

    except catch_aws_error("AccessDeniedException", "UnauthorizedAccess*"):
        print(f"::error::Access denied to ECR repository '{repo_name}' — check IAM permissions", file=sys.stderr)
        sys.exit(3)

    except Exception as e:
        print(f"::error::Unexpected error resolving {repo_name}:{tag}: {e}", file=sys.stderr)
        sys.exit(4)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <repo_name> <tag>", file=sys.stderr)
        sys.exit(4)
    digest = resolve_digest(sys.argv[1], sys.argv[2])
    print(digest)
