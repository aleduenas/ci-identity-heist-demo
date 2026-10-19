# Network module

Two AZs, public/private /24 subnets, DNS-enabled VPC, one NAT gateway, and a DynamoDB gateway endpoint. Nodes never receive public IPs. The single NAT reduces lab complexity and has an AZ failure and cross-AZ transfer cost tradeoff. Outbound access is necessary for ECR, STS, EKS Auth, package mirrors and the GitHub runner. Endpoint policy is AWS's default; IAM table policies remain the authorization boundary. No inbound app listener, VPN, or runner is created.
