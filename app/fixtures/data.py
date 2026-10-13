"""Clearly fictional records; reruns never reset an existing balance."""

CUSTOMERS = [
    {"customer_id": "cust-alice", "name": "Alice Synthetic", "email": "alice@example.invalid"},
    {"customer_id": "cust-bob", "name": "Bob Synthetic", "email": "bob@example.invalid"},
]
ACCOUNTS = [
    {
        "account_id": "acct-alice",
        "customer_id": "cust-alice",
        "currency": "CAD",
        "balance_cents": 100_000,
    },
    {
        "account_id": "acct-bob",
        "customer_id": "cust-bob",
        "currency": "CAD",
        "balance_cents": 25_000,
    },
]
