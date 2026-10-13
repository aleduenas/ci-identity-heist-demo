# Evidence and observability

## Application requests

`kubectl logs -n mybank deployment/mybank-api` returns structured JSON request events: request ID, method, route template, HTTP status and latency. The API returns its request ID in `X-Request-ID`. Logs exclude API keys, bodies, customer fields, account identifiers and arbitrary unknown request paths. A shared lab API key identifies the service caller collectively; it does not attribute requests to individual customers or employees.

These logs stay with the pod/container runtime. There is no CloudWatch application-log shipping add-on in this milestone. Save relevant events before replacing pods. Do not treat transient pod logs as durable audit evidence.

## Kubernetes and AWS identity

EKS control-plane logging enables API, audit, authenticator, controller-manager and scheduler logs in `/aws/eks/<cluster>/cluster` with 30-day retention. Use audit/authenticator events to distinguish Kubernetes authorization denials from network or identity failures. Pod readiness verifies table reads under the workload's Pod Identity credentials.

CloudTrail captures management events and data events for the three synthetic tables. Its private, encrypted, versioned S3 audit bucket is given by `audit_bucket_name`. Check delivered S3 objects for data events; CloudTrail's default Event history is not the data-event archive. Role session names distinguish employee sessions, CI run IDs identify releases, and the workload role identifies app table activity. Delivery can take several minutes.

## Identity-provider evidence

The local Keycloak realm enables login and admin event recording. Its container logs and admin event views help verify group membership changes and federation failures. Do not persist assertions or temporary AWS credentials in an evidence document. Signed claims prove what the local IdP emitted; only successful AWS federation proves IAM accepted them.

## Record a normal-operation baseline

Before an exercise, record the infrastructure revision, app commit/digest, expected role matrix, a successful transfer with matching retry, a rejected overdraft, and the corresponding request/CloudTrail/EKS timestamps. Record which audit sources are retained and their delivery delay. Use UTC timestamps inside technical evidence while keeping the exercise schedule in your local timezone.

## Limits

This milestone has no SIEM, centralized application logging, metric dashboard, alert rules, distributed tracing or immutable cross-account archive. State and audit buckets block automatic deletion but privileged account administrators can still alter the lab. Session Manager does not capture port-forward payloads. Kubernetes NetworkPolicy enforcement and IAM/SAML behaviour require live acceptance tests.

[CloudTrail data events](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html), [EKS control-plane logs](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html), [Session Manager logging limits](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-logging.html).
