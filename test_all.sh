#!/bin/bash

echo "╔══════════════════════════════════════════╗"
echo "║    ПОЛНОЕ ТЕСТИРОВАНИЕ API СИСТЕМЫ      ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Проверка доступности сервера..."
echo "=========================================="

# Проверяем доступность сервера на порту 8080
if ! curl -s --head http://localhost:8080 > /dev/null; then
    echo "❌ Сервер не запущен на localhost:8080"
    echo "Запустите: python manage.py runserver 8080"
    exit 1
fi

echo "✅ Сервер доступен на http://localhost:8080"

# Функция для получения токена из ответа
extract_token() {
    echo "$1" | python3 -c "
import sys, json, re

try:
    # Убираем часть с HTTP кодом если есть
    response_text = sys.stdin.read()
    if '| HTTP:' in response_text:
        json_part = response_text.split('| HTTP:')[0].strip()
    else:
        json_part = response_text
    
    data = json.loads(json_part)
    
    # Проверяем разные форматы ответа
    if 'access' in data:
        print(data['access'])
    elif 'tokens' in data and 'access' in data['tokens']:
        print(data['tokens']['access'])
    else:
        print('')
except Exception as e:
    print('')
"
}

# Функция для извлечения refresh токена
extract_refresh() {
    echo "$1" | python3 -c "
import sys, json, re

try:
    response_text = sys.stdin.read()
    if '| HTTP:' in response_text:
        json_part = response_text.split('| HTTP:')[0].strip()
    else:
        json_part = response_text
    
    data = json.loads(json_part)
    
    if 'refresh' in data:
        print(data['refresh'])
    elif 'tokens' in data and 'refresh' in data['tokens']:
        print(data['tokens']['refresh'])
    else:
        print('')
except Exception as e:
    print('')
"
}

# Простая функция тестирования
test_simple() {
    echo ""
    echo "=== $1 ==="
    echo "URL: $2"
    echo "Метод: $3"
    
    if [ -n "$4" ]; then
        echo "Данные: $4"
    fi
    
    if [ -n "$5" ]; then
        echo "Токен: ${5:0:30}..."
    fi
    
    local response
    if [ -n "$4" ] && [ -n "$5" ]; then
        # С данными и токеном
        response=$(curl -s -w " | HTTP: %{http_code}" -X $3 "$2" \
            -H "Authorization: Bearer $5" \
            -H "Content-Type: application/json" \
            -d "$4" 2>/dev/null)
    elif [ -n "$5" ]; then
        # Только токен
        response=$(curl -s -w " | HTTP: %{http_code}" -X $3 "$2" \
            -H "Authorization: Bearer $5" 2>/dev/null)
    elif [ -n "$4" ]; then
        # Только данные
        response=$(curl -s -w " | HTTP: %{http_code}" -X $3 "$2" \
            -H "Content-Type: application/json" \
            -d "$4" 2>/dev/null)
    else
        # Без данных и токена
        response=$(curl -s -w " | HTTP: %{http_code}" -X $3 "$2" 2>/dev/null)
    fi
    
    echo "Ответ: $response"
    
    # Извлекаем HTTP код
    http_code=$(echo "$response" | grep -o 'HTTP: [0-9]*' | cut -d' ' -f2)
    
    if [[ "$http_code" =~ ^2[0-9][0-9]$ ]]; then
        echo "✅ Успешно (HTTP $http_code)"
        return 0
    elif [[ "$http_code" =~ ^4[0-9][0-9]$ ]]; then
        echo "⚠️  Ошибка клиента (HTTP $http_code)"
        return 1
    else
        echo "❌ Ошибка (HTTP $http_code)"
        return 1
    fi
}

echo ""
echo "1. ТЕСТИРОВАНИЕ АУТЕНТИФИКАЦИИ"
echo "=========================================="

# 1.1 Регистрация нового пользователя
test_simple \
    "Регистрация нового пользователя" \
    "http://localhost:8080/api/auth/register/" \
    "POST" \
    '{
        "email": "test_user_'$(date +%s)'@example.com",
        "password": "TestPass123!",
        "password2": "TestPass123!",
        "first_name": "Тест",
        "last_name": "Пользователь"
    }'

# 1.2 Логин пользователя user1
echo ""
echo "=== Логин пользователя user1 ==="
USER_RESPONSE=$(curl -s -X POST "http://localhost:8080/api/auth/login/" \
    -H "Content-Type: application/json" \
    -d '{"email": "user1@example.com", "password": "User123!"}')

echo "Ответ: $USER_RESPONSE"
USER_TOKEN=$(extract_token "$USER_RESPONSE")

if [ -n "$USER_TOKEN" ] && [ "$USER_TOKEN" != "ERROR_TOKEN" ]; then
    echo "✅ Токен пользователя получен: ${USER_TOKEN:0:30}..."
else
    echo "❌ Не удалось получить токен пользователя"
    echo "Создайте пользователя через: python create_test_data.py"
    exit 1
fi

# 1.3 Логин менеджера
echo ""
echo "=== Логин менеджера ==="
MANAGER_RESPONSE=$(curl -s -X POST "http://localhost:8080/api/auth/login/" \
    -H "Content-Type: application/json" \
    -d '{"email": "manager@example.com", "password": "Manager123!"}')

echo "Ответ: $MANAGER_RESPONSE"
MANAGER_TOKEN=$(extract_token "$MANAGER_RESPONSE")

if [ -n "$MANAGER_TOKEN" ]; then
    echo "✅ Токен менеджера получен: ${MANAGER_TOKEN:0:30}..."
else
    echo "⚠️  Не удалось получить токен менеджера"
    echo "Запустите: python create_test_data.py"
fi

# 1.4 Логин администратора
echo ""
echo "=== Логин администратора ==="
ADMIN_RESPONSE=$(curl -s -X POST "http://localhost:8080/api/auth/login/" \
    -H "Content-Type: application/json" \
    -d '{"email": "admin@example.com", "password": "Admin123!"}')

echo "Ответ: $ADMIN_RESPONSE"
ADMIN_TOKEN=$(extract_token "$ADMIN_RESPONSE")

if [ -n "$ADMIN_TOKEN" ]; then
    echo "✅ Токен администратора получен: ${ADMIN_TOKEN:0:30}..."
else
    echo "⚠️  Не удалось получить токен администратора"
    echo "Запустите: python create_test_data.py"
fi

echo ""
echo "2. ТЕСТИРОВАНИЕ ПРОФИЛЯ ПОЛЬЗОВАТЕЛЯ"
echo "=========================================="

if [ -n "$USER_TOKEN" ]; then
    test_simple \
        "Получение профиля пользователя" \
        "http://localhost:8080/api/auth/profile/" \
        "GET" \
        "" \
        "$USER_TOKEN"
    
    test_simple \
        "Обновление профиля" \
        "http://localhost:8080/api/auth/profile/" \
        "PATCH" \
        '{"first_name": "Обновленное", "last_name": "Имя"}' \
        "$USER_TOKEN"
fi

echo ""
echo "3. ТЕСТИРОВАНИЕ БИЗНЕС-ЛОГИКИ"
echo "=========================================="

if [ -n "$USER_TOKEN" ]; then
    test_simple \
        "Список проектов (пользователь)" \
        "http://localhost:8080/api/projects/" \
        "GET" \
        "" \
        "$USER_TOKEN"
    
    test_simple \
        "Панель управления" \
        "http://localhost:8080/api/dashboard/" \
        "GET" \
        "" \
        "$USER_TOKEN"
    
    test_simple \
        "Попытка создания проекта обычным пользователем" \
        "http://localhost:8080/api/projects/create/" \
        "POST" \
        '{"name": "Проект пользователя", "description": "Попытка создания"}' \
        "$USER_TOKEN"
fi

if [ -n "$MANAGER_TOKEN" ]; then
    test_simple \
        "Создание проекта менеджером" \
        "http://localhost:8080/api/projects/create/" \
        "POST" \
        '{"name": "Проект менеджера", "description": "Создан менеджером"}' \
        "$MANAGER_TOKEN"
fi

echo ""
echo "4. ТЕСТИРОВАНИЕ ОШИБОК ДОСТУПА"
echo "=========================================="

test_simple \
    "Демо ошибки 401 (без токена)" \
    "http://localhost:8080/api/demo/access/?type=401" \
    "GET"

test_simple \
    "Демо ошибки 403" \
    "http://localhost:8080/api/demo/access/?type=403" \
    "GET"

test_simple \
    "Доступ к проектам без токена" \
    "http://localhost:8080/api/projects/" \
    "GET"

echo ""
echo "5. ТЕСТИРОВАНИЕ АДМИНИСТРАТИВНЫХ ФУНКЦИЙ"
echo "=========================================="

if [ -n "$ADMIN_TOKEN" ]; then
    test_simple \
        "Получение списка ролей (админ)" \
        "http://localhost:8080/api/auth/roles/" \
        "GET" \
        "" \
        "$ADMIN_TOKEN"
    
    test_simple \
        "Получение списка разрешений (админ)" \
        "http://localhost:8080/api/auth/permissions/" \
        "GET" \
        "" \
        "$ADMIN_TOKEN"
    
    test_simple \
        "Получение списка назначений ролей (админ)" \
        "http://localhost:8080/api/auth/user-roles/" \
        "GET" \
        "" \
        "$ADMIN_TOKEN"
fi

if [ -n "$USER_TOKEN" ]; then
    test_simple \
        "Попытка доступа к ролям без прав админа" \
        "http://localhost:8080/api/auth/roles/" \
        "GET" \
        "" \
        "$USER_TOKEN"
fi

echo ""
echo "6. ТЕСТИРОВАНИЕ ДОКУМЕНТОВ"
echo "=========================================="

if [ -n "$USER_TOKEN" ]; then
    test_simple \
        "Список документов" \
        "http://localhost:8080/api/documents/" \
        "GET" \
        "" \
        "$USER_TOKEN"
    
    test_simple \
        "Скачивание документа (мок)" \
        "http://localhost:8080/api/documents/550e8400-e29b-41d4-a716-446655440001/download/" \
        "GET" \
        "" \
        "$USER_TOKEN"
fi

echo ""
echo "7. ТЕСТИРОВАНИЕ ВЫХОДА И ОБНОВЛЕНИЯ ТОКЕНА"
echo "=========================================="

if [ -n "$USER_TOKEN" ]; then
    # Получаем refresh токен
    USER_REFRESH=$(extract_refresh "$USER_RESPONSE")
    
    if [ -n "$USER_REFRESH" ]; then
        test_simple \
            "Обновление токена" \
            "http://localhost:8080/api/auth/refresh/" \
            "POST" \
            "{\"refresh\": \"$USER_REFRESH\"}"
        
        test_simple \
            "Выход из системы" \
            "http://localhost:8080/api/auth/logout/" \
            "POST" \
            "{\"refresh\": \"$USER_REFRESH\"}" \
            "$USER_TOKEN"
    else
        echo "⚠️  Не удалось получить refresh токен для тестирования"
    fi
fi

echo ""
echo "══════════════════════════════════════════"
echo "✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!"
echo "══════════════════════════════════════════"