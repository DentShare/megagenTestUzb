# Скрипт для проверки и запуска PostgreSQL
# Использование: .\check_postgres.ps1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Проверка PostgreSQL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Поиск службы PostgreSQL
$postgresServices = Get-Service | Where-Object {$_.Name -like "*postgresql*"}

if ($postgresServices.Count -eq 0) {
    Write-Host "❌ Служба PostgreSQL не найдена!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Возможные решения:" -ForegroundColor Yellow
    Write-Host "1. PostgreSQL не установлен"
    Write-Host "2. Служба имеет другое имя"
    Write-Host ""
    Write-Host "Попробуйте найти службу вручную:" -ForegroundColor Yellow
    Write-Host "   Get-Service | Where-Object {`$_.DisplayName -like '*PostgreSQL*'}" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Или откройте 'Службы' (services.msc) и найдите PostgreSQL" -ForegroundColor Yellow
    exit 1
}

Write-Host "Найдено служб PostgreSQL: $($postgresServices.Count)" -ForegroundColor Green
Write-Host ""

foreach ($service in $postgresServices) {
    Write-Host "Служба: $($service.DisplayName)" -ForegroundColor Cyan
    Write-Host "  Имя: $($service.Name)" -ForegroundColor Gray
    Write-Host "  Статус: $($service.Status)" -ForegroundColor $(if ($service.Status -eq 'Running') { 'Green' } else { 'Red' })
    
    if ($service.Status -ne 'Running') {
        Write-Host ""
        Write-Host "  ⚠️  Служба остановлена. Попытка запуска..." -ForegroundColor Yellow
        try {
            Start-Service -Name $service.Name
            Start-Sleep -Seconds 3
            $service.Refresh()
            if ($service.Status -eq 'Running') {
                Write-Host "  ✅ Служба успешно запущена!" -ForegroundColor Green
            } else {
                Write-Host "  ❌ Не удалось запустить службу" -ForegroundColor Red
                Write-Host "  Попробуйте запустить от имени администратора:" -ForegroundColor Yellow
                Write-Host "    net start $($service.Name)" -ForegroundColor Gray
            }
        } catch {
            Write-Host "  ❌ Ошибка при запуске: $_" -ForegroundColor Red
            Write-Host "  Попробуйте запустить от имени администратора:" -ForegroundColor Yellow
            Write-Host "    net start $($service.Name)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ✅ Служба работает" -ForegroundColor Green
    }
    Write-Host ""
}

# Проверка порта 5432
Write-Host "Проверка порта 5432..." -ForegroundColor Cyan
$portCheck = Test-NetConnection -ComputerName localhost -Port 5432 -WarningAction SilentlyContinue

if ($portCheck.TcpTestSucceeded) {
    Write-Host "✅ Порт 5432 доступен" -ForegroundColor Green
} else {
    Write-Host "❌ Порт 5432 недоступен" -ForegroundColor Red
    Write-Host "   PostgreSQL может быть не запущен или использует другой порт" -ForegroundColor Yellow
}
Write-Host ""

# Проверка подключения к базе данных через Python
Write-Host "Проверка подключения к базе данных..." -ForegroundColor Cyan
Write-Host ""

$pythonCheck = python check_db.py 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Подключение к базе данных успешно!" -ForegroundColor Green
} else {
    Write-Host "❌ Ошибка подключения к базе данных" -ForegroundColor Red
    Write-Host ""
    Write-Host "Проверьте:" -ForegroundColor Yellow
    Write-Host "1. Настройки в файле .env" -ForegroundColor Yellow
    Write-Host "2. Существует ли база данных (запустите: python init_db.py)" -ForegroundColor Yellow
    Write-Host "3. Правильность пароля в .env файле" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
