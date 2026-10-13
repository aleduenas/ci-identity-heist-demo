# Operations module

Optional private AL2023 t3.small host with encrypted disk, no public IP, no inbound rules, and only the SSM managed-instance IAM policy. NAT permits agent and software downloads. User data installs Docker, git, Python, unzip and jq; cloud-init completion must be checked before use. There are no SSH keys, GitHub registration tokens, or EKS admin permissions in instance metadata or user data.

Use SSM remote-host forwarding for private EKS access or manually register a trusted self-hosted GitHub runner here. The operator's separate IAM role authorizes SSM sessions; the host IAM role does not. Installing a runner and Docker access creates a trusted release boundary: never execute untrusted pull requests on this host. Add kubectl/AWS CLI/runner tooling as described in the delivery guide. Set `enable_operations_host=false` when providing an existing VPC-connected host.
