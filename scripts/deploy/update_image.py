"""Deploy an immutable image using namespace-scoped release credentials."""

import argparse
import subprocess

from common import checked_image, kubeconfig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    image = checked_image(args.image)
    with kubeconfig(args.cluster, args.region) as command:
        subprocess.run(
            command + ["-n", "mybank", "set", "image", "deployment/mybank-api", f"api={image}"],
            check=True,
        )
        subprocess.run(
            command
            + ["-n", "mybank", "rollout", "status", "deployment/mybank-api", "--timeout=300s"],
            check=True,
        )


if __name__ == "__main__":
    main()
