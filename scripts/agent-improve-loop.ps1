# Agent improvement loop — tick every 5 seconds
$payload = '{"prompt":"улучшай, добавляй новые функции, делай красивее, исправляй ошибки. Начинай следующий loop через 5 секунд после завершение старого"}'
while ($true) {
    Start-Sleep -Seconds 5
    Write-Output "AGENT_LOOP_TICK_aitteam $payload"
}
