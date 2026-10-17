# Reach the private EKS API

AWS provisioning uses AWS public service APIs; Kubernetes bootstrap uses the private cluster endpoint. The optional operations module supplies a private AL2023 host with no inbound security-group rules and only an SSM instance role. It can forward traffic to EKS while your workstation keeps the administrator credentials. It is also the trusted GitHub runner host.

Install AWS CLI v2, the AWS Session Manager plugin, kubectl and the Python project environment on your workstation. Authenticate as an operator that has permission to start/terminate SSM sessions on this host and an EKS access entry matching a bootstrap administrator ARN. The instance role cannot grant itself cluster access.

In terminal one, with your provisioning/admin AWS profile selected:

```bash
python scripts/access/start_api_tunnel.py --outputs .cache/outputs.json
```

The script prints the endpoint hostname and starts the SSM remote-host tunnel on `127.0.0.1:8443`. Leave it open. In terminal two, use the same AWS profile and set:

```bash
export MYBANK_KUBE_API_SERVER=https://127.0.0.1:8443
export MYBANK_KUBE_TLS_SERVER_NAME=<hostname-printed-by-the-tunnel>
```

PowerShell equivalents are `$env:MYBANK_KUBE_API_SERVER = 'https://127.0.0.1:8443'` and `$env:MYBANK_KUBE_TLS_SERVER_NAME = '<hostname>'`. The [bootstrap helper](delivery.md) uses these variables to configure its temporary kubeconfig, retaining the EKS CA and verifying the real EKS certificate name. It never uses `--insecure-skip-tls-verify`.

For direct kubectl after bootstrap, create your normal kubeconfig using `aws eks update-kubeconfig --name <cluster> --region us-east-1`. Obtain its cluster identifier with `kubectl config view -o json`, then run:

```bash
kubectl config set-cluster <cluster-identifier> \
  --server=https://127.0.0.1:8443 --tls-server-name=<eks-hostname>
kubectl get pods -n mybank
kubectl -n mybank port-forward service/mybank-api 8000:8000
```

Use the bootstrap/admin session for port-forwarding. Engineer RBAC deliberately excludes `pods/portforward` and `pods/exec`. Authenticate the API with your lab key in the request header. Restore the original cluster server with `aws eks update-kubeconfig` when moving to a VPC-connected machine. Unset the `MYBANK_KUBE_*` tunnel variables on the runner.

Employee roles do not get SSM access automatically. Test engineer kubectl permissions from the VPC host or use an administrator-owned tunnel while obtaining an engineer SAML session separately. Being able to reach the endpoint does not grant Kubernetes permissions.

Session Manager port-forwarding transports encrypted traffic; its payload is not captured in session logs. CloudTrail records session initiation, EKS audit logs record API requests, and DynamoDB table data events record the AWS data operations.

[AWS Session Manager remote-host port forwarding](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html)
