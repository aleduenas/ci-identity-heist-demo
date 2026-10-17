# Dot-source from PowerShell to use the repository-local AWS CLI and temporary login.
$taskRepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$taskAwsDir = Join-Path $taskRepoRoot '.tools/aws-cli/portable/Amazon/AWSCLIV2'
$taskAwsCache = Join-Path $taskRepoRoot '.cache/aws'
if (-not (Test-Path -LiteralPath (Join-Path $taskAwsDir 'aws.exe'))) {
    throw 'The verified AWS CLI has not been extracted into .tools/aws-cli/portable.'
}
$taskSsmDir = Join-Path $taskRepoRoot '.tools/session-manager/portable/bin'
$env:PATH = $taskAwsDir + [IO.Path]::PathSeparator + $taskSsmDir + [IO.Path]::PathSeparator + $env:PATH
$env:AWS_CONFIG_FILE = Join-Path $taskAwsCache 'config'
$env:AWS_SHARED_CREDENTIALS_FILE = Join-Path $taskAwsCache 'credentials'
$env:AWS_LOGIN_CACHE_DIRECTORY = Join-Path $taskAwsCache 'login'
$env:AWS_PROFILE = 'codex-builder'
$env:AWS_REGION = 'ca-central-1'
$env:AWS_DEFAULT_REGION = 'ca-central-1'
$env:AWS_PAGER = ''
