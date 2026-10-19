"""Explicit environment contract shared by API and fixture tooling."""

import os
from dataclasses import dataclass

import boto3
from botocore.config import Config


@dataclass(frozen=True)
class Settings:
    region: str = "us-east-1"
    endpoint_url: str | None = None
    customers_table: str = "mybank-customers"
    accounts_table: str = "mybank-accounts"
    transfers_table: str = "mybank-transfers"
    api_key: str = ""

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            region=os.getenv("AWS_REGION", "us-east-1"),
            endpoint_url=os.getenv("DYNAMODB_ENDPOINT_URL") or None,
            customers_table=os.getenv("CUSTOMERS_TABLE", "mybank-customers"),
            accounts_table=os.getenv("ACCOUNTS_TABLE", "mybank-accounts"),
            transfers_table=os.getenv("TRANSFERS_TABLE", "mybank-transfers"),
            api_key=os.getenv("APP_API_KEY", ""),
        )

    def dynamodb_client(self):
        return boto3.client(
            "dynamodb",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
            config=Config(
                connect_timeout=2,
                read_timeout=5,
                retries={"mode": "standard", "total_max_attempts": 3},
            ),
        )
