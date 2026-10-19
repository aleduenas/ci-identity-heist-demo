# Evidence and observability

## Live control evidence

The signals below distinguish a successful attack, an enabled policy, a denied
retry and a legitimate check. See the [security control](../security/README.md)
for how enforcement is deployed.

| Signal | Establishes | Does not establish |
| --- | --- | --- |
| Obtained exercise identity plus nonempty table output | The lab attack reached synthetic data | Production access or a webhook transfer |
| BEFORE/DESIRED/SAVED AND VERIFIED | IAM stored the desired trust policy | Revocation of old sessions or instant global propagation |
| Fresh STS authorization denial | This probe stopped before deployment credentials | A guarantee about unrelated actors or jobs |
| Harmless PR status/checks green | Normal proposed-code checks still work | Successful AWS role issuance |
| Same-role main-access job green | Main can still obtain the exercise role | Full application rollout |

No terminal monitor is required for activation: the main GitHub workflow calls IAM.
The optional collector remains separate supporting visibility. Its main-workflow
allowlist currently excludes the newer control workflow, so those main events can
produce context_not_verified without implying that enforcement failed.

The normal API sanitizes its request logs. The attack deliberately changes the
container command and prints synthetic table results through pod logs into Actions.
Application logging conventions do not prevent arbitrary replacement workload code
from producing different output. Retain marker/count evidence, not raw record values.

## Application requests

`kubectl logs -n mybank deployment/mybank-api` returns structured JSON request events: request ID, method, route template, HTTP status and latency. The API returns its request ID in `X-Request-ID`. Logs exclude API keys, bodies, customer fields, account identifiers and arbitrary unknown request paths. A shared lab API key identifies the service caller collectively; it does not attribute requests to individual customers or employees.

These logs stay with the pod/container runtime. There is no CloudWatch application-log shipping add-on in this milestone. Save relevant events before replacing pods. Do not treat transient pod logs as durable audit evidence.

## Kubernetes and AWS identity

EKS control-plane logging enables API, audit, authenticator, controller-manager and scheduler logs in `/aws/eks/<cluster>/cluster` with 30-day retention. Use audit/authenticator events to distinguish Kubernetes authorization denials from network or identity failures. Pod readiness verifies table reads under the workload's Pod Identity credentials.

CloudTrail captures management events and data events for the three synthetic tables.
Its private encrypted/versioned S3 audit bucket is given by audit_bucket_name.
Check delivered S3 objects for data events; default Event history is not the table
data-event archive. Session names are labels and cannot establish trusted CI origin.
For STS issuance, use AWS's accepted GitHub subject plus independently matched
run/attempt metadata. The workload role identifies app table activity. Delivery
can take several minutes; the historical collector timing is an observation, not a guarantee.

## Identity-provider evidence

The local Keycloak realm enables login and admin event recording. Its container logs and admin event views help verify group membership changes and federation failures. Do not persist assertions or temporary AWS credentials in an evidence document. Signed claims prove what the local IdP emitted; only successful AWS federation proves IAM accepted them.

## Record a normal-operation baseline

Before an exercise, record the infrastructure revision, app commit/digest, expected role matrix, a successful transfer with matching retry, a rejected overdraft, and the corresponding request/CloudTrail/EKS timestamps. Record which audit sources are retained and their delivery delay. Use UTC timestamps inside technical evidence while keeping the exercise schedule in your local timezone.

## Limits

This milestone has no SIEM, centralized application-log shipping, metric dashboard,
managed paging, distributed tracing or immutable cross-account archive. A custom
collector/detector exists, but it is optional and has no automatic response or
session revocation. State/audit buckets resist automatic deletion; account
administrators can still alter the lab. Session Manager does not capture port-forward
payloads. NetworkPolicy and employee SAML need their own live acceptance evidence.

[CloudTrail data events](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html), [EKS control-plane logs](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html), [Session Manager logging limits](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-logging.html).
