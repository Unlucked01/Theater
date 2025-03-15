# Система заказа билетов

Веб-приложение для заказа билетов на мероприятия, написанное на Perl с использованием CGI.

## Требования

- Perl 5.10 или выше
- SQLite3
- Модули Perl (установка через cpan):
  - CGI::Simple
  - DBI
  - DBD::SQLite
  - Template
  - Crypt::PBKDF2
  - JSON
  - DateTime
  - File::Spec
  - MIME::Base64

## Установка

1. Установите необходимые модули Perl:
```bash
cpan CGI::Simple DBI DBD::SQLite Template Crypt::PBKDF2 JSON DateTime File::Spec MIME::Base64
```

2. Создайте базу данных:
```bash
perl database/init_db.pl
```

3. Настройте права доступа:
```bash
chmod +x index.cgi
chmod 755 templates static
chmod 644 static/*/*.{css,js}
```

## Структура проекта

```
.
├── index.cgi           # Основной CGI-скрипт
├── database/
│   ├── init_db.pl     # Скрипт инициализации БД
│   ├── init.sql       # SQL-схема БД
│   └── theater.db     # База данных SQLite
├── templates/         # HTML-шаблоны
├── static/           # Статические файлы
│   ├── css/
│   ├── js/
│   └── images/
└── README.md
```

## Роли пользователей

1. Покупатель
   - Просмотр мероприятий
   - Добавление билетов в корзину
   - Оформление заказов

2. Менеджер
   - Создание мероприятий
   - Управление заказами

3. Администратор
   - Просмотр статистики
   - Управление пользователями

## Запуск

1. Разместите проект в директории веб-сервера с поддержкой CGI
2. Откройте в браузере http://your-server/path/to/index.cgi

## Учетные данные по умолчанию

- Администратор:
  - Логин: admin
  - Пароль: admin123 