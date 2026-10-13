"""Regression checks for access boundaries and immutable rendering."""

import json
import tempfile
import unittest
from pathlib import Path

import yaml
from common import checked_image
from render import BASE, render


class DeploymentContractTest(unittest.TestCase):
    def test_employee_and_release_roles_exclude_escalation_resources(self):
        for path in (BASE / "rbac").glob("*.yaml"):
            role = next(
                item for item in yaml.safe_load_all(path.read_text()) if item["kind"] == "Role"
            )
            for rule in role["rules"]:
                self.assertFalse(
                    set(rule["resources"]) & {"*", "secrets", "pods/exec", "roles", "rolebindings"}
                )
                self.assertFalse(
                    set(rule["verbs"])
                    & {"*", "create", "delete", "bind", "escalate", "impersonate"}
                )
        deployment_role = list(yaml.safe_load_all((BASE / "rbac/deployers.yaml").read_text()))[0]
        self.assertEqual(deployment_role["rules"][0]["resourceNames"], ["mybank-api"])

    def test_tag_and_repository_must_be_immutable(self):
        repository = "123456789012.dkr.ecr.ca-central-1.amazonaws.com/mybank-api"
        self.assertEqual(
            checked_image(repository + ":" + "a" * 40, repository), repository + ":" + "a" * 40
        )
        for image in (repository + ":latest", repository + ":main", "docker.io/example/api:latest"):
            with self.assertRaises(ValueError):
                checked_image(image, repository)
        with self.assertRaises(ValueError):
            checked_image(repository + ":" + "a" * 40, repository + "-other")

    def test_render_uses_real_output_names_and_preserves_security_context(self):
        repository = "123456789012.dkr.ecr.ca-central-1.amazonaws.com/mybank-api"
        values = {
            "ecr_repository_url": repository,
            "aws_region": "ca-central-1",
            "customers_table_name": "actual-customers",
            "accounts_table_name": "actual-accounts",
            "transfers_table_name": "actual-transfers",
        }
        with tempfile.TemporaryDirectory() as directory:
            outputs = Path(directory) / "outputs.json"
            outputs.write_text(json.dumps({key: {"value": value} for key, value in values.items()}))
            resources = render(outputs, repository + "@sha256:" + "b" * 64)
        deployment = next(item for item in resources if item["kind"] == "Deployment")
        pod = deployment["spec"]["template"]["spec"]
        container = pod["containers"][0]
        environment = {item["name"]: item.get("value") for item in container["env"]}
        self.assertEqual(environment["ACCOUNTS_TABLE"], "actual-accounts")
        self.assertNotIn("DYNAMODB_ENDPOINT_URL", environment)
        self.assertFalse(pod["automountServiceAccountToken"])
        self.assertTrue(container["securityContext"]["readOnlyRootFilesystem"])
        self.assertFalse(container["securityContext"]["allowPrivilegeEscalation"])


if __name__ == "__main__":
    unittest.main()
