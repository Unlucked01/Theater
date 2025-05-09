# Система заказа билетов в театр

Веб-приложение для заказа билетов на театральные представления и другие мероприятия, написанное на Perl с использованием CGI. Система позволяет выбирать места из разных зон зала одновременно, просматривать интерактивную схему зала и управлять заказами.

## Ключевые функции

- Интерактивная схема зала с визуальным отображением зон и мест
- Мультизональный выбор мест (возможность выбрать места из разных зон одновременно)
- Отображение цен билетов для каждой зоны
- Корзина заказа с расчетом общей стоимости
- Управление бронированием и покупкой билетов
- Административный интерфейс для создания мероприятий и управления заказами

## Запуск через Docker

Проект настроен для запуска в контейнере Docker, что значительно упрощает процесс развертывания.

### Требования

- Docker
- Docker Compose

### Запуск

1. Клонируйте репозиторий:
```bash
git clone <url-репозитория>
cd theater
```

2. Запустите приложение через Docker Compose:
```bash
docker-compose up -d
```

3. Приложение будет доступно по адресу: http://localhost:8090

### Docker Entrypoint

Проект использует скрипт `docker-entrypoint.sh`, который выполняет следующие функции:

- Проверка и настройка прав доступа для директорий
- Инициализация базы данных (если она не существует)
- Проверка наличия всех необходимых таблиц в базе данных
- При необходимости, пересоздание базы данных из SQL-схемы

## Структура проекта

```
.
├── cgi-bin/           # CGI-скрипты
│   └── index.cgi     # Основной CGI-скрипт
├── database/
│   ├── init.sql      # SQL-схема БД
│   └── theater.db    # База данных SQLite (создается автоматически)
├── templates/         # HTML-шаблоны
│   ├── layout.html    # Основной шаблон страницы
│   ├── index.html     # Главная страница
│   ├── events.html    # Список мероприятий
│   ├── select_zone.html # Выбор мест и зон
│   ├── cart.html      # Корзина заказа
│   └── ...            # Другие шаблоны
├── static/           # Статические файлы
│   ├── css/
│   ├── js/
│   └── images/
├── Dockerfile        # Конфигурация Docker-образа
├── docker-compose.yml # Конфигурация Docker Compose
├── docker-entrypoint.sh # Скрипт инициализации контейнера
└── README.md
```

## Процесс бронирования

1. Пользователь выбирает мероприятие из списка
2. Открывается интерактивная схема зала с отображением зон и мест
3. Пользователь может выбрать места из разных зон одновременно
4. При выборе места отображается его стоимость и общая сумма заказа
5. Пользователь добавляет выбранные места в корзину
6. В корзине можно оформить заказ или продолжить выбор мест

## Роли пользователей

1. Покупатель
   - Просмотр мероприятий
   - Выбор и бронирование мест из разных зон
   - Добавление билетов в корзину
   - Оформление заказов

2. Менеджер
   - Создание мероприятий
   - Управление заказами и бронированием
   - Просмотр статистики продаж

3. Администратор
   - Просмотр общей статистики
   - Управление пользователями
   - Настройка системы

## Учетные данные по умолчанию

- Администратор:
  - Логин: admin
  - Пароль: admin123 

## Ручная установка (без Docker)

Если требуется запустить проект без использования Docker:

1. Установите требуемые зависимости:
   - Perl 5.10 или выше
   - SQLite3
   - Perl модули: CGI::Simple, DBI, DBD::SQLite, Template, Crypt::PBKDF2, JSON, DateTime, File::Spec, MIME::Base64

2. Установите модули Perl:
```bash
cpan CGI::Simple DBI DBD::SQLite Template Crypt::PBKDF2 JSON DateTime File::Spec MIME::Base64
```

3. Создайте базу данных:
```bash
sqlite3 database/theater.db < database/init.sql
```

4. Настройте права доступа:
```bash
chmod +x cgi-bin/index.cgi
chmod 755 templates static
chmod 644 static/*/*.{css,js}
```

5. Настройте веб-сервер (Apache, Nginx) для работы с CGI-скриптами 