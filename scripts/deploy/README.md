# Operator tooling

Run from the repository root with Python 3.12, PyYAML, AWS CLI v2 and kubectl matching the EKS minor version. `render.py` reads Terraform's typed output JSON and emits reviewable YAML. `bootstrap.py` requires an EKS bootstrap administrator and `APP_API_KEY` in the process environment. `update_image.py` runs with the narrow GitHub deployment role after bootstrap.

Temporary kubeconfigs are removed after each command. Tools never alter the default local Kubernetes context. `test_contract.py` checks image immutability, output substitution and the access-control boundary using `python -m unittest discover -s scripts/deploy -p 'test_*.py'`.
