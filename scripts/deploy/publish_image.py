"""Publish a commit image once, reusing its immutable ECR digest on retries."""

import argparse
import re
import subprocess
from pathlib import Path

from common import checked_image


def existing_digest(repository: str, commit: str) -> str | None:
    result = subprocess.run(
        [
            "aws",
            "ecr",
            "describe-images",
            "--repository-name",
            repository,
            "--image-ids",
            f"imageTag={commit}",
            "--query",
            "imageDetails[0].imageDigest",
            "--output",
            "text",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        if "(ImageNotFoundException)" in result.stderr:
            return None
        raise RuntimeError(f"ECR image lookup failed: {result.stderr.strip()}")
    digest = result.stdout.strip()
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("ECR returned an invalid image digest")
    return digest


def publish(repository_url: str, commit: str) -> str:
    image = checked_image(f"{repository_url}:{commit}")
    registry, repository = repository_url.split("/", 1)
    digest = existing_digest(repository, commit)
    if digest:
        print("Commit image already exists; reusing its immutable digest")
        return f"{repository_url}@{digest}"
    password = subprocess.run(
        ["aws", "ecr", "get-login-password"], capture_output=True, text=True, check=True
    ).stdout
    try:
        subprocess.run(
            ["docker", "login", "--username", "AWS", "--password-stdin", registry],
            input=password,
            text=True,
            check=True,
        )
        subprocess.run(["docker", "build", "--tag", image, "."], check=True)
        subprocess.run(["docker", "push", image], check=True)
    finally:
        subprocess.run(["docker", "logout", registry], stdout=subprocess.DEVNULL, check=False)
    digest = existing_digest(repository, commit)
    if not digest:
        raise RuntimeError("ECR image missing after successful push")
    return f"{repository_url}@{digest}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True, help="GitHub job output file")
    args = parser.parse_args()
    image = publish(args.repository, args.commit)
    with args.output.open("a", encoding="utf-8") as output:
        output.write(f"image={image}\n")
    print(f"Release image: {image}")


if __name__ == "__main__":
    main()
