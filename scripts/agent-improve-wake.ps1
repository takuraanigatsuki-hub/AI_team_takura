# One-shot wake: next improvement cycle 5s after previous completes (dynamic loop)
Start-Sleep -Seconds 5
Write-Output 'AGENT_LOOP_WAKE_aitteam {"prompt":"/loop improve add features fix bugs make UI prettier next cycle 5s after previous completes"}'
