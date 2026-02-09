# Быстрое решение проблемы с PostgreSQL

## Проблема: "Удаленный компьютер отклонил это сетевое подключение"

Это означает, что PostgreSQL сервер **не запущен** или **не установлен**.

## Быстрое решение

### Шаг 1: Проверьте, установлен ли PostgreSQL

Откройте PowerShell и выполните:

```powershell
Get-Service | Where-Object {$_.DisplayName -like "*PostgreSQL*"}
```

Если ничего не найдено - PostgreSQL не установлен. Перейдите к [установке](#установка-postgresql).

### Шаг 2: Запустите PostgreSQL

Если служба найдена, но остановлена:

**Вариант А: Через PowerShell (от имени администратора)**
```powershell
# Найдите имя службы
Get-Service | Where-Object {$_.DisplayName -like "*PostgreSQL*"}

# Запустите службу (замените имя на ваше)
net start postgresql-x64-15
# или
net start postgresql-x64-16
```

**Вариант Б: Через графический интерфейс**
1. Нажмите `Win + R`
2. Введите `services.msc` и нажмите Enter
3. Найдите службу PostgreSQL
4. Правой кнопкой → "Запустить"

### Шаг 3: Проверьте подключение

После запуска PostgreSQL, проверьте подключение:

```powershell
python check_db.py
```

Или запустите бота:

```powershell
python main.py
```

## Установка PostgreSQL

Если PostgreSQL не установлен:

### Вариант 1: Установка через установщик

1. Скачайте PostgreSQL: https://www.postgresql.org/download/windows/
2. Запустите установщик
3. Во время установки:
   - Запомните пароль для пользователя `postgres`
   - Порт по умолчанию: `5432`
4. После установки запустите службу

### Вариант 2: Установка через Docker (если установлен Docker)

```powershell
docker run --name postgres-megagen `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=megagen_bot `
  -p 5432:5432 `
  -d postgres:15
```

Затем в `.env` файле:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=megagen_bot
DB_USER=postgres
DB_PASS=postgres
```

### Вариант 3: Использование облачной БД

Можно использовать бесплатные облачные базы данных:
- **Supabase**: https://supabase.com
- **Neon**: https://neon.tech
- **Railway**: https://railway.app

## После установки/запуска

1. Создайте базу данных:
```powershell
python init_db.py
```

2. Проверьте подключение:
```powershell
python check_db.py
```

3. Запустите бота:
```powershell
python main.py
```

## Полезные команды

```powershell
# Проверка статуса службы
Get-Service | Where-Object {$_.DisplayName -like "*PostgreSQL*"}

# Запуск службы
net start postgresql-x64-15

# Остановка службы
net stop postgresql-x64-15

# Проверка порта
Test-NetConnection -ComputerName localhost -Port 5432
```

## Если ничего не помогает

1. Проверьте файл `.env` - правильны ли настройки?
2. Проверьте, не занят ли порт 5432 другим приложением:
   ```powershell
   netstat -an | findstr 5432
   ```
3. Перезагрузите компьютер
4. Переустановите PostgreSQL
