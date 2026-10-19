"""Render Kustomize templates with values from the actual Terraform outputs."""

import argparse
import subprocess
from pathlib import Path

import yaml
from common import checked_image, terraform_outputs

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "deploy" / "kubernetes" / "base"


def substitute(value, replacements):
    if isinstance(value, dict):
        return {key: substitute(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute(item, replacements) for item in value]
    if isinstance(value, str):
        if value in replacements:
            return replacements[value]
        if value.startswith("__") and value.endswith("__"):
            raise ValueError(f"Unresolved placeholder: {value}")
    return value


def render(outputs_path: Path, image: str) -> list[dict]:
    outputs = terraform_outputs(outputs_path)
    replacements = {
        "__IMAGE__": checked_image(image, outputs["ecr_repository_url"]),
        "__AWS_REGION__": outputs["aws_region"],
        "__CUSTOMERS_TABLE__": outputs["customers_table_name"],
        "__ACCOUNTS_TABLE__": outputs["accounts_table_name"],
        "__TRANSFERS_TABLE__": outputs["transfers_table_name"],
    }
    for value in replacements.values():
        if not isinstance(value, str) or not value:
            raise ValueError("Terraform output replacement must be a nonempty string")
    result = subprocess.run(
        ["kubectl", "kustomize", str(BASE)], capture_output=True, text=True, check=True
    )
    return [substitute(item, replacements) for item in yaml.safe_load_all(result.stdout)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "deploy/generated/mybank.yaml")
    args = parser.parse_args()
    resources = render(args.outputs, args.image)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(yaml.safe_dump_all(resources, sort_keys=False), encoding="utf-8")
    print(f"Rendered {len(resources)} resources to {args.out}")


if __name__ == "__main__":
    main()
