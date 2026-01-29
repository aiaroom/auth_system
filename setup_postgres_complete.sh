#!/bin/bash

echo "Полная настройка PostgreSQL для Django..."

DB_NAME="auth_system"
DB_USER="auth_user"
DB_PASSWORD="auth_password"

# Останавливаем все соединения с базой
sudo -u postgres psql <<EOF
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity 
WHERE pg_stat_activity.datname = '$DB_NAME' 
  AND pid <> pg_backend_pid();
EOF

# Удаляем старые объекты
sudo -u postgres psql <<EOF
DROP DATABASE IF EXISTS $DB_NAME;
DROP USER IF EXISTS $DB_USER;
EOF

# Создаем суперпользователя для Django
sudo -u postgres psql <<EOF
CREATE USER $DB_USER WITH 
    PASSWORD '$DB_PASSWORD'
    SUPERUSER
    CREATEDB
    CREATEROLE
    INHERIT
    LOGIN
    REPLICATION
    BYPASSRLS;
EOF

# Создаем базу данных
sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME 
    WITH OWNER = $DB_USER
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0
    CONNECTION LIMIT = -1;
EOF

# Даем все права
sudo -u postgres psql -d $DB_NAME <<EOF
-- Делаем пользователя владельцем всей БД
ALTER DATABASE $DB_NAME OWNER TO $DB_USER;

-- Даем все права на схему public
GRANT ALL ON SCHEMA public TO $DB_USER WITH GRANT OPTION;
ALTER SCHEMA public OWNER TO $DB_USER;

-- Даем права на создание таблиц в будущем
ALTER DEFAULT PRIVILEGES FOR USER $DB_USER IN SCHEMA public 
    GRANT ALL ON TABLES TO $DB_USER;
    
ALTER DEFAULT PRIVILEGES FOR USER $DB_USER IN SCHEMA public 
    GRANT ALL ON SEQUENCES TO $DB_USER;
    
ALTER DEFAULT PRIVILEGES FOR USER $DB_USER IN SCHEMA public 
    GRANT ALL ON FUNCTIONS TO $DB_USER;
    
ALTER DEFAULT PRIVILEGES FOR USER $DB_USER IN SCHEMA public 
    GRANT ALL ON TYPES TO $DB_USER;
EOF

echo "Настройка завершена!"
echo "Пользователь создан как SUPERUSER - имеет все права"