# PowerShell лаунчер для системы обработки сертификатов
# Запуск: .\run_certificates.ps1

param(
    [switch]$Auto,  # Автоматический запуск всех этапов
    [switch]$Check  # Только проверка системы
)

# Заголовок
Write-Host "===============================================" -ForegroundColor Green
Write-Host "      СИСТЕМА ОБРАБОТКИ СЕРТИФИКАТОВ" -ForegroundColor Yellow
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""

# Проверяем наличие Python
Write-Host " Проверка Python..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " Python найден: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python не найден"
    }
} catch {
    Write-Host " Python не установлен или недоступен!" -ForegroundColor Red
    Write-Host " Установите Python: https://python.org" -ForegroundColor Yellow
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Проверяем наличие main.py
$mainScript = "main.py"
if (-not (Test-Path $mainScript)) {
    Write-Host " Файл $mainScript не найден!" -ForegroundColor Red
    Write-Host " Убедитесь, что все файлы находятся в одной папке" -ForegroundColor Yellow
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host "Все файлы найдены" -ForegroundColor Green
Write-Host ""

# Устанавливаем кодировку для корректного отображения русского текста
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Запускаем main.py с параметрами
if ($Auto) {
    Write-Host " Автоматический запуск полной обработки..." -ForegroundColor Yellow
    Write-Host ""
    # Здесь можно добавить автоматический запуск
    python $mainScript
} elseif ($Check) {
    Write-Host " Запуск проверки системы..." -ForegroundColor Yellow
    Write-Host ""
    python $mainScript
} else {
    Write-Host " Запуск интерактивного интерфейса..." -ForegroundColor Yellow
    Write-Host ""
    python $mainScript
}

# Проверяем код выхода
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host " Программа завершилась с ошибкой (код: $LASTEXITCODE)" -ForegroundColor Red
} else {
    Write-Host ""
    Write-Host " Программа завершилась успешно" -ForegroundColor Green
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Read-Host "Нажмите Enter для закрытия"