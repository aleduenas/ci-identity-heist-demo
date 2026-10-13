"""Local table bootstrap and explicit, insert-only AWS synthetic seeding."""

import argparse
from urllib.parse import urlparse

from botocore.exceptions import ClientError

from app.fixtures.data import ACCOUNTS, CUSTOMERS
from app.repository.codec import encode
from app.settings import Settings


def create_local_tables(client, settings: Settings) -> None:
    endpoint = urlparse(settings.endpoint_url or "")
    if endpoint.hostname not in {"localhost", "127.0.0.1", "dynamodb", "dynamodb-local"}:
        raise ValueError("Local bootstrap requires a loopback or Compose DynamoDB endpoint")
    for table, key in [
        (settings.customers_table, "customer_id"),
        (settings.accounts_table, "account_id"),
        (settings.transfers_table, "transfer_id"),
    ]:
        try:
            client.create_table(
                TableName=table,
                KeySchema=[{"AttributeName": key, "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": key, "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
        except ClientError as error:
            if error.response["Error"]["Code"] != "ResourceInUseException":
                raise
        client.get_waiter("table_exists").wait(
            TableName=table,
            WaiterConfig={"Delay": 1, "MaxAttempts": 30},
        )


def seed_existing_tables(client, settings: Settings) -> None:
    for table, key, records in [
        (settings.customers_table, "customer_id", CUSTOMERS),
        (settings.accounts_table, "account_id", ACCOUNTS),
    ]:
        for item in records:
            try:
                client.put_item(
                    TableName=table,
                    Item=encode(item),
                    ConditionExpression=f"attribute_not_exists({key})",
                )
            except ClientError as error:
                if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
                    raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local", action="store_true", help="Create local tables and seed")
    mode.add_argument("--aws", action="store_true", help="Seed existing AWS tables only")
    arguments = parser.parse_args()
    settings = Settings.from_environment()
    if arguments.aws and settings.endpoint_url:
        parser.error("--aws requires DYNAMODB_ENDPOINT_URL to be unset")
    if arguments.local and not settings.endpoint_url:
        parser.error("--local requires DYNAMODB_ENDPOINT_URL")
    client = settings.dynamodb_client()
    try:
        if arguments.local:
            create_local_tables(client, settings)
        seed_existing_tables(client, settings)
    finally:
        client.close()
    print("Synthetic fixtures present; existing records were preserved.")


if __name__ == "__main__":
    main()
