$lines = Get-Content .env
$seen = @{}
$out = @()
foreach ($l in $lines) {
    if ($l -match '^([A-Z_]+)=') {
        $k = $Matches[1]
        if ($seen.ContainsKey($k)) { continue }
        $seen[$k] = $true
    }
    if ($l.Trim() -ne "") { $out += $l }
}
Set-Content .env $out
Get-Content .env | ForEach-Object { ($_ -split "=")[0] }