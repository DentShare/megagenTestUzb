# Инструкция по настройке PostgreSQL

## Проблема: "Удаленный компьютер отклонил это сетевое подключение"

Эта ошибка означает, что PostgreSQL сервер не запущен или недоступен.

## Решение

### 1. Проверка статуса PostgreSQL (Windows)

#### Способ 1: Через службы Windows
1. Нажмите `Win + R`
2. Введите `services.msc` и нажмите Enter
3. Найдите службу PostgreSQL (обычно называется `postgresql-x64-XX` или `PostgreSQL`)
4. Если статус "Остановлена" - нажмите правой кнопкой → "Запустить"

#### Способ 2: Через командную строку
```powershell
# Проверка статуса службы
Get-Service | Where-Object {$_.Name -like "*postgresql*"}

# Запуск службы (замените имя на ваше)
net start postgresql-x64-15
# или
net start postgresql-x64-16
```

### 2. Установка PostgreSQL (если не установлен)

1. Скачайте PostgreSQL: https://www.postgresql.org/download/windows/
2. Установите с настройками по умолчанию
3. Запомните пароль для пользователя `postgres`
4. Убедитесь, что служба запущена

### 3. Настройка подключения

Создайте или обновите файл `.env` в корне проекта:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=megagen_bot
DB_USER=postgres
DB_PASS=ваш_пароль_от_postgres
```

### 4. Создание базы данных

После запуска PostgreSQL, создайте базу данных:

```powershell
# Вариант 1: Через psql
psql -U postgres
CREATE DATABASE megagen_bot;
\q

# Вариант 2: Через Python скрипт
python init_db.py
```

### 5. Проверка подключения

Запустите скрипт проверки:

```powershell
python check_db.py
```

Этот скрипт проверит:
- ✅ Подключение к серверу
- ✅ Существование базы данных
- ✅ Наличие таблиц
- ✅ Данные в таблицах

## Альтернативные решения

### Использование Docker (если установлен)

```powershell
# Запуск PostgreSQL в Docker
docker run --name postgres-megagen `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=megagen_bot `
  -p 5432:5432 `
  -d postgres:15

# Проверка
docker ps
```

В `.env` файле:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=megagen_bot
DB_USER=postgres
DB_PASS=postgres
```

### Использование SQLite (для тестирования)

Если PostgreSQL недоступен, можно временно использовать SQLite для тестирования.
Однако это потребует изменения кода и не рекомендуется для продакшена.

## Полезные команды

```powershell
# Проверка, слушает ли PostgreSQL порт 5432
netstat -an | findstr 5432

# Проверка подключения через telnet
Test-NetConnection -ComputerName localhost -Port 5432

# Просмотр логов PostgreSQL (обычно в папке установки)
# C:\Program Files\PostgreSQL\XX\data\log\
```

## Частые проблемы

### Проблема: "Служба не запускается"
**Решение:**
1. Проверьте логи PostgreSQL
2. Убедитесь, что порт 5432 не занят другим приложением
3. Переустановите PostgreSQL

### Проблема: "Неверный пароль"
**Решение:**
1. Сбросьте пароль через pgAdmin или psql
2. Обновите DB_PASS в .env файле

### Проблема: "База данных не существует"
**Решение:**
```powershell
python init_db.py
```

## После успешной настройки

1. Запустите проверку: `python check_db.py`
2. Если все ОК, запустите бота: `python main.py`
