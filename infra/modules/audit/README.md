# Audit module

A multi-region CloudTrail records management events and read/write DynamoDB data events scoped to the lab's three tables. Logs go to a private, versioned SSE-S3 bucket with TLS enforcement. Delivery grants are restricted to this trail ARN and account prefix. Log-file integrity validation produces digests; it does not make logs immutable against the AWS account administrator.

Data events incur additional charges. S3 logs persist until deliberately removed, with no automatic expiration to preserve exercise evidence. `force_destroy=false` protects accidental loss; archive evidence and remove every version/delete marker before teardown. DynamoDB data events are inspected in S3 (or an operator-configured query service), not the default CloudTrail Event History view. CloudWatch control-plane logging belongs to the EKS module.
