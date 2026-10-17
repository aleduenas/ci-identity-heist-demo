# Local AWS operator session

The AWS CLI and Session Manager plugin live in the ignored `.tools/` directory, extracted from the official signed installers. No long-lived access key is used: the CLI signs in with your console IAM user's temporary session.

Sign in once per session (a browser approval):

```powershell
.venv/Scripts/python.exe -m scripts.demo.login
```

That writes two ignored profiles to `.cache/aws/config`: `demo-admin-login` (the console login session) and `demo-admin` (exports those temporary credentials to boto3 and Terraform). Run any command with them through the wrapper:

```powershell
.venv/Scripts/python.exe -m scripts.aws.run aws sts get-caller-identity
```

Or dot-source the session into an interactive PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. ./scripts/aws/session.ps1
aws sts get-caller-identity
```

The operator defaults to IAM user `demo-admin` in `us-east-1`; set `MYBANK_AWS_USER` to use another IAM user. Local configuration and refresh credentials stay under ignored `.cache/aws/`; never commit or print their contents.
