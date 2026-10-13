# Transactional application

This is a fictional bank API with two synthetic accounts, not a customer-facing banking product. It provides realistic data access and transactional behavior for the EKS environment. Employee SAML federation controls AWS access; a separate shared lab API key protects application routes. The key gives access to all synthetic account and transfer endpoints. It does not implement individual customer authorization, employee attribution, payments, account creation, or real money movement.

## Package boundaries

| Path | Responsibility |
| --- | --- |
| `app/main.py` | ASGI construction, lifecycle, sanitized error mapping |
| `app/settings.py` | Environment configuration and bounded AWS client timeouts |
| `app/observability.py` | Structured request logs and bounded correlation IDs |
| `app/api/` | Authentication dependencies, probes, HTTP routes |
| `app/schemas.py` | Strict inputs and explicit response schemas |
| `app/service.py`, `app/domain.py` | Use cases and business failure vocabulary |
| `app/repository/` | Consistent reads, value serialization, atomic transaction construction and retries |
| `app/fixtures/` | Explicit local table bootstrap and insert-only synthetic seeding |
| `tests/app/` | Moto-backed transactions, API contracts, fixture safeguards |

## Configuration

| Variable | Default / purpose |
| --- | --- |
| `AWS_REGION` | `ca-central-1` |
| `DYNAMODB_ENDPOINT_URL` | Unset for AWS; `http://dynamodb:8000` in Compose |
| `CUSTOMERS_TABLE` | `mybank-customers` |
| `ACCOUNTS_TABLE` | `mybank-accounts` |
| `TRANSFERS_TABLE` | `mybank-transfers` |
| `APP_API_KEY` | No default credential; business routes deny access and readiness fails when unset/empty |

In AWS, boto3 uses the default credential chain and EKS Pod Identity. For DynamoDB Local, use dummy `AWS_ACCESS_KEY_ID=local` and `AWS_SECRET_ACCESS_KEY=local`; they are emulator placeholders, never AWS credentials. The API runs on port 8000 with `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Only `/health` and `/ready` expose unauthenticated operational information; they return no records or credentials. OpenAPI documentation describes schemas without returning customer data.

The runtime IAM role needs `GetItem` on all three tables, and permission to update accounts and insert transfers through `TransactWriteItems`. Readiness uses a sentinel `GetItem` on each table, so it needs no `DescribeTable` permission. The role needs no table creation, scans, or fixture writes. Readiness verifies configured credentials, table existence and read access; a controlled transfer verifies write permissions separately.

## API contract

Supply the credential in `X-API-Key` for every business route. Use a randomly generated key kept outside Git. The application uses constant-time comparison and returns 401 for missing or incorrect credentials. A key change requires a pod restart because configuration is read at process startup.

| Route | Authentication | Result |
| --- | --- | --- |
| `GET /health` | None | Process health, 200 |
| `GET /ready` | None | Configured key and readable tables, 200 or sanitized 503 |
| `GET /accounts/{account_id}` | API key | Account owner ID, CAD currency and balance in integer cents |
| `POST /transfers` | API key | Immutable transfer record; matching retry returns the same record, 200 |
| `GET /transfers/{transfer_id}` | API key | Previously committed transfer or 404 |

Example request body:

```json
{
  "transfer_id": "demo-transfer-001",
  "source_account_id": "acct-alice",
  "destination_account_id": "acct-bob",
  "amount_cents": 1234
}
```

The response contains those four fields plus `currency: "CAD"`, an ISO 8601 UTC `created_at`, and `actor: "lab-api"`. Actor is assigned by the service because the shared lab credential cannot identify a person. Unknown input fields, invalid identifiers, same-account transfers, float/string/bool amounts, zero/negative amounts and amounts above 1,000,000,000 cents return 422. IDs contain 1–100 ASCII letters, digits, underscores or hyphens.

Missing accounts or transfers return 404. A transfer ID reused with different account IDs or amount returns 409 `idempotency_conflict`; overdrafts and destination balance-limit violations also return 409. Accounts must both use CAD; other currency values return 422. Storage failures return sanitized 503 responses, without leaking AWS exception details or table names. Retry 503 responses with the same transfer ID and payload.

## Transaction guarantees

Each transfer performs one DynamoDB `TransactWriteItems`: conditional debit, conditional credit, and conditional ledger insert. Conditions are evaluated together at commit, so a change after prevalidation cannot cause an overdraft, unsupported currency transfer, or partial balance change. The destination maximum is 1,000,000,000,000 cents. Account keys must already exist. All monetary values are integer cents; no floating point calculation is used.

The immutable `transfer_id` ledger entry is the durable idempotency key. Strongly consistent reads check it before writes and after transaction cancellation or an ambiguous timeout. A concurrent winner is returned for matching parameters; differing parameters conflict. A second attempt cannot debit again because its ledger insert condition fails and the whole transaction rolls back. Idempotency lasts as long as the ledger is retained; the environment does not configure ledger TTL. Administrative deletion of ledger entries breaks that guarantee and is outside the app's normal permissions.

The repository makes at most three transaction attempts with short backoff. The SDK also has a bounded retry policy. Persistent conflicts, throttling or ambiguous failures eventually return 503, allowing the caller to retry later. DynamoDB Local and Moto approximate AWS behavior; real conflict behavior, networking, IAM conditions and Pod Identity require the deployed environment checks.

## Synthetic fixtures

`python -m app.fixtures.seed --local` requires an explicit local endpoint. It creates the customers/accounts/transfers tables if absent and seeds two customers and accounts. Creation is restricted to loopback or the Compose host names `dynamodb` and `dynamodb-local`; the API never calls it automatically. For another container hostname, change the explicit allowlist during integration.

`python -m app.fixtures.seed --aws` requires `DYNAMODB_ENDPOINT_URL` to be unset. It only inserts synthetic records into tables already created by Terraform; it never calls `CreateTable`. Run it under an operator role with conditional `PutItem` permission on customers/accounts, not the application role. Supply Terraform output table names as environment variables. This mode is explicit because it mutates the provisioned lab.

| Customer | Account | Initial balance |
| --- | --- | --- |
| `cust-alice`, Alice Synthetic, `alice@example.invalid` | `acct-alice` | 100,000 CAD cents |
| `cust-bob`, Bob Synthetic, `bob@example.invalid` | `acct-bob` | 25,000 CAD cents |

Seeding is insert-only, using `attribute_not_exists` conditions. Reruns preserve balances and existing customer records. Partial initial seeding can safely be rerun. Transfers are never seeded or reset. To start over locally, remove the disposable DynamoDB Local volume using the documented Compose teardown; AWS table deletion is an explicit infrastructure teardown operation.

## Verification and container

Install with `python -m pip install -e '.[dev]'`, then run `python -m pytest tests/app` and `ruff check app tests/app`. Tests use Moto with real boto3 transaction calls against an emulated backend. Coverage includes conserved balances, immutable ledger retries, parameter conflicts, rejected overdrafts and missing accounts, currency and balance limits, a competing writer, commit-response loss, bounded conflict retries, authentication, request validation, missing configuration, readiness failure, and AWS fixture creation refusal.

The Dockerfile uses the Python 3.12 Debian slim runtime, direct dependency version pins in `pyproject.toml`, and nonroot UID/GID 10001. It starts one Uvicorn process, makes no GPU assumption, supports a read-only root filesystem, and disables HTTP access logs to avoid logging request IDs/paths. The Python minor-version base tag intentionally follows security patch updates; record an image digest and a complete dependency lock before an immutable release. Kubernetes resource limits and probes live in `deploy/`, not application code.

The application emits one JSON request event to stdout with `event`, `request_id`, HTTP `method`, normalized `route` template, response `status`, and `latency_ms`. For example, an account read logs `/accounts/{account_id}` rather than its actual account ID; unmatched URLs log `<unmatched>`. Headers, request/response bodies, account/customer/transfer values and API keys are omitted. Every handled response includes `X-Request-ID`. An incoming correlation ID is accepted only if it is 1–64 ASCII letters, digits, underscores or hyphens; otherwise a new UUID hex value is generated. Use `kubectl logs deployment/mybank-api -n mybank` to inspect events during exercises. These workload logs are separate from EKS control-plane CloudWatch audit logs; persistent application-log export is an optional future integration.

Application tests were run locally on Python 3.14; the CI/runtime target is Python 3.12. The HTTPX-backed Starlette test client currently emits a deprecation warning; it does not affect the runtime or assertions. CI is the Python 3.12 compatibility check. No live AWS or EKS deployment is implied by these tests.

References: [DynamoDB transactions and cancellation behavior](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html), [FastAPI lifespan initialization](https://fastapi.tiangolo.com/advanced/events/), and [Starlette releases](https://starlette.dev/release-notes/).
