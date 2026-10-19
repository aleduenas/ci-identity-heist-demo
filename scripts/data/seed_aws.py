"""Insert absent synthetic fixtures into the account represented by Terraform outputs."""
import argparse
import json
from pathlib import Path

import boto3

from app.fixtures.seed import seed_existing_tables
from app.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs", required=True, type=Path)
    args = parser.parse_args()
    raw = json.loads(args.outputs.read_text(encoding="utf-8-sig"))
    values = {name: item["value"] for name, item in raw.items()}
    account = boto3.client("sts", region_name=values["aws_region"]).get_caller_identity()["Account"]
    if account != values["identity_configuration"]["account_id"]:
        raise SystemExit("AWS account differs from Terraform outputs; no fixtures were written")
    settings = Settings(
        region=values["aws_region"], customers_table=values["customers_table_name"],
        accounts_table=values["accounts_table_name"],
        transfers_table=values["transfers_table_name"],
    )
    client = settings.dynamodb_client()
    try:
        seed_existing_tables(client, settings)
    finally:
        client.close()
    print("Synthetic fixtures inserted where absent; existing balances were preserved")


if __name__ == "__main__":
    main()
