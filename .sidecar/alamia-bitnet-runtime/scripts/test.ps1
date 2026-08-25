$ErrorActionPreference = "Stop"
Write-Host "Testing BitNet Inference Provider at http://localhost:8080/v1/chat/completions..." -ForegroundColor Cyan

$body = @{
    model = "bitnet_b1_58_2b"
    messages = @(
        @{
            role = "user"
            content = "Explain the advantages of 1-bit ternary quantization in one sentence."
        }
    )
    temperature = 0.2
    max_tokens = 64
} | ConvertTo-Json -Depth 5

$t0 = Get-Date
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:8080/v1/chat/completions" -Method Post -Body $body -ContentType "application/json"
    $dur = (Get-Date) - $t0
    Write-Host "[OK] Response received in $($dur.TotalMilliseconds)ms:" -ForegroundColor Green
    Write-Host $resp.choices[0].message.content -ForegroundColor White
} catch {
    Write-Host "[ERROR] Could not connect to BitNet server at http://localhost:8080: $_" -ForegroundColor Red
}
