import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from app.fixtures.seed import create_local_tables, seed_existing_tables
from app.main import create_app
from app.repository.dynamodb import BankRepository
from app.settings import Settings


@pytest.fixture
def settings():
    return Settings(api_key="unit-test-key", endpoint_url="http://localhost:8000")


@pytest.fixture
def repository(settings):
    with mock_aws():
        client = boto3.client("dynamodb", region_name=settings.region)
        create_local_tables(client, settings)
        seed_existing_tables(client, settings)
        yield BankRepository(client, settings)


@pytest.fixture
def api(repository, settings):
    with TestClient(create_app(settings, repository)) as client:
        client.headers["X-API-Key"] = settings.api_key
        yield client
