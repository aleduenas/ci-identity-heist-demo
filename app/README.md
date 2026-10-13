# Mybank application

The FastAPI API moves synthetic CAD balances between accounts, with an immutable DynamoDB transfer ledger. See [application operations and API contract](../docs/application.md) for setup, request examples, tests, and limitations.

Packages follow dependency direction from `api/` routes to `service.py`, business rules in `domain.py`, and `repository/` persistence. `settings.py` supplies the environment contract. `fixtures/` is explicit operator tooling; the API never creates tables or seeds records at startup.

Entrypoint: `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Fixture entrypoint: `python -m app.fixtures.seed --local` or `--aws`.
