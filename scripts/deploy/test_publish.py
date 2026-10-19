"""Check release retry behavior without contacting ECR or Docker."""

import subprocess
import unittest
from unittest.mock import patch

from publish_image import existing_digest, publish


class PublishTest(unittest.TestCase):
    def test_existing_tag_reuses_digest_without_rebuilding(self):
        digest = "sha256:" + "a" * 64
        with patch("publish_image.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, digest, "")
            repository = "123456789012.dkr.ecr.us-east-1.amazonaws.com/mybank-api"
            self.assertEqual(publish(repository, "b" * 40), f"{repository}@{digest}")
            self.assertEqual(run.call_count, 1)

    def test_only_missing_image_allows_first_publish(self):
        with patch("publish_image.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess(
                [], 254, "", "An error occurred (ImageNotFoundException)"
            )
            self.assertIsNone(existing_digest("mybank-api", "b" * 40))

    def test_lookup_permissions_failure_is_not_treated_as_missing_image(self):
        with patch("publish_image.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess(
                [], 254, "", "An error occurred (AccessDeniedException)"
            )
            with self.assertRaisesRegex(RuntimeError, "AccessDeniedException"):
                existing_digest("mybank-api", "b" * 40)


if __name__ == "__main__":
    unittest.main()
