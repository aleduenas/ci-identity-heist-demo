from dataclasses import replace

import pytest

from app.fixtures.seed import create_local_tables


@pytest.mark.parametrize("endpoint", [None, "https://dynamodb.us-east-1.amazonaws.com"])
def test_local_bootstrap_never_creates_aws_tables(repository, settings, endpoint):
    with pytest.raises(ValueError, match="Local bootstrap"):
        create_local_tables(repository.client, replace(settings, endpoint_url=endpoint))
