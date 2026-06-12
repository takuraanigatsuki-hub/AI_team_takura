# Agent improvement loop — tick every 5 seconds (UTF-8 safe payload)
$payload = '{"prompt":"/loop improve add features fix bugs make UI prettier start next iteration 5s after previous completes"}'
while ($true) {
    Start-Sleep -Seconds 5
    Write-Output "AGENT_LOOP_TICK_aitteam $payload"
}
