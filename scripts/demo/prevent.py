"""Toggle prevention: `on` removes PR trust from the exercise deploy role (main-only); `off`
restores the deliberately weak detection-mode trust. Only that one trust policy changes."""

import argparse
import json

from scripts.demo import gh
from scripts.demo.ops import CACHE, TFVARS, activate, ok, save_outputs, step, terraform, tf_vars


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["on", "off"])
    args = parser.parse_args()
    activate()
    repo = gh.repository()
    allow_pr = args.mode == "off"
    settings = json.loads(TFVARS.read_text(encoding="utf-8"))
    settings["allow_pr_demo"] = allow_pr
    TFVARS.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    step(f"Prevention {args.mode}: exercise role trusts PR jobs = {allow_pr}")
    plan = str(CACHE / "prevent.tfplan")
    terraform("plan", "-input=false", "-no-color", *tf_vars(repo), f"-out={plan}", capture=True)
    result = terraform("apply", "-input=false", "-no-color", plan, capture=True)
    print("    " + next((line for line in result.splitlines() if line.startswith("Apply complete")),
                         "applied"), flush=True)
    patterns = save_outputs()["detection_subject_patterns"]
    for pattern in patterns:
        print(f"    trusts {pattern.split(':', 2)[2]}")
    ok("IAM changes can take ~10-30 s to apply everywhere before re-running the attack")


if __name__ == "__main__":
    main()
