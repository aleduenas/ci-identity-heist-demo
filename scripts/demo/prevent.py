"""Retired local Terraform toggle; control deployment now lives in GitHub Actions."""


def main():
    raise SystemExit("Edit security/control.json on trusted main, then watch Deploy security "
                     "control in GitHub Actions. See security/README.md. This command makes "
                     "no local or AWS changes.")


if __name__ == "__main__":
    main()
