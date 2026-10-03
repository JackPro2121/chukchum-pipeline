$ErrorActionPreference = "Stop"
$repo = "JackPro2121/chukchum-pipeline"

function Get-EnvValue($name) {
    $line = Get-Content .env | Where-Object { $_ -like "$name=*" } | Select-Object -First 1
    if (-not $line) { throw "$name not found in .env" }
    return $line.Substring($name.Length + 1)
}

$secrets = @{
    "APIFY_TOKEN"    = Get-EnvValue "APIFY_TOKEN"
    "OLLAMA_API_KEY" = Get-EnvValue "OLLAMA_API_KEY"
    "BUFFER_API_KEY" = Get-EnvValue "BUFFER_API_KEY"
    "MEDIA_REPO_TOKEN" = (gh auth token)
}

foreach ($k in $secrets.Keys) {
    gh secret set $k --repo $repo --body $secrets[$k] | Out-Null
    Write-Output "set $k (len $($secrets[$k].Length))"
}

gh secret list --repo $repo