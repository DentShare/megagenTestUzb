@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
echo ============================================================
echo Проверка и запуск PostgreSQL
echo ============================================================
echo.

REM Поиск службы PostgreSQL
echo Поиск службы PostgreSQL...
for /f "tokens=*" %%i in ('sc query state^= all ^| findstr /i "postgresql"') do (
    echo Найдено: %%i
)

echo.
echo Попытка найти и запустить службу PostgreSQL...
echo.

REM Попытка запустить различные варианты имен служб
set SERVICES=postgresql-x64-15 postgresql-x64-16 postgresql-x64-14 postgresql-x64-13 postgresql-x64-12 postgresql-x64-11 postgresql-x64-10 postgresql-x64-9 postgresql-x64-8 postgresql-x64-7 postgresql-x64-6 postgresql-x64-5 postgresql-x64-4 postgresql-x64-3 postgresql-x64-2 postgresql-x64-1 postgresql-x64-0 postgresql-x64 postgresql

for %%s in (%SERVICES%) do (
    sc query "%%s" >nul 2>&1
    if !errorlevel! equ 0 (
        echo Найдена служба: %%s
        sc query "%%s" | findstr /i "RUNNING" >nul
        if !errorlevel! equ 0 (
            echo   Статус: Запущена
        ) else (
            echo   Статус: Остановлена
            echo   Попытка запуска...
            net start "%%s"
            if !errorlevel! equ 0 (
                echo   Успешно запущена!
                goto :check_port
            ) else (
                echo   Ошибка запуска. Требуются права администратора.
            )
        )
        goto :check_port
    )
)

echo.
echo ============================================================
echo PostgreSQL не найден!
echo ============================================================
echo.
echo Возможные решения:
echo 1. PostgreSQL не установлен - установите с https://www.postgresql.org/download/windows/
echo 2. Служба имеет другое имя - проверьте в services.msc
echo.
echo Нажмите любую клавишу для открытия окна служб...
pause >nul
services.msc
exit /b 1

:check_port
echo.
echo ============================================================
echo Проверка порта 5432...
echo ============================================================
netstat -an | findstr ":5432" >nul
if !errorlevel! equ 0 (
    echo Порт 5432 активен
) else (
    echo Порт 5432 не активен
)

echo.
echo ============================================================
echo Проверка завершена
echo ============================================================
echo.
echo Теперь попробуйте запустить:
echo   python check_db.py
echo.
pause
endlocal
