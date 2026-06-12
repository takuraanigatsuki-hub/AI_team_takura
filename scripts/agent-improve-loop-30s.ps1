# Fixed improvement loop — tick every 30 seconds
$payload = '{"prompt":"/loop improve project: fix bugs, add features, prettier UI. Next cycle immediately after previous completes."}'
while ($true) {
    Start-Sleep -Seconds 30
    Write-Output "AGENT_LOOP_TICK_aitteam $payload"
}
