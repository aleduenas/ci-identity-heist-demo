# EKS module

Private endpoint, API access entries, explicitly named bootstrap admin roles, AL2023 managed nodes, encrypted gp3 disks, IMDSv2 with hop limit 1, and all control-plane logs retained 30 days. Two t3.medium nodes are a small lab default; this is not a banking availability guarantee. Node IAM permits EKS operation, CNI networking and ECR pull, with no DynamoDB access. The CNI uses its managed policy on the node role; application identity is separate.

Managed VPC CNI is installed before nodes; CoreDNS, kube-proxy and Pod Identity agent follow nodes. Compatible add-on versions are resolved by AWS and visible in plans; pin `addon_versions` after review for repeatable updates. VPC CNI network policy is enabled in standard mode: a newly starting pod can briefly communicate until its policies are reconciled. Strict startup enforcement requires additional kube-system policies and live testing before enabling.

The default EKS version is composed by the environment. Review the AWS lifecycle before apply; STANDARD support avoids extended-support enrollment and causes AWS to upgrade a version when standard support ends. Plan node/add-on upgrades ahead of that date. Private clients need VPC routing/DNS plus IAM/RBAC; being inside the VPC alone does not grant Kubernetes access.
