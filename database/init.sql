DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);

DROP TABLE IF EXISTS events;
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    performers TEXT,
    venue TEXT,
    description TEXT,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    price REAL NOT NULL,
    available_seats INTEGER NOT NULL
);

DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    zone_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    total_price REAL NOT NULL,
    status TEXT NOT NULL,
    seat_numbers TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (zone_id) REFERENCES zones(id)
);

DROP TABLE IF EXISTS zones;
CREATE TABLE zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    total_seats INTEGER NOT NULL,
    description TEXT
);

DROP TABLE IF EXISTS event_zones;
CREATE TABLE event_zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    zone_id INTEGER NOT NULL,
    available_seats INTEGER NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (zone_id) REFERENCES zones(id)
);

DROP TABLE IF EXISTS cart;
CREATE TABLE cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    zone_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    total_price REAL NOT NULL,
    seat_numbers TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (zone_id) REFERENCES zones(id)
);

-- Table for tracking reserved seats
DROP TABLE IF EXISTS reserved_seats;
CREATE TABLE reserved_seats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    zone_id INTEGER NOT NULL,
    seat_number INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    reservation_type TEXT NOT NULL, -- 'cart', 'order', 'temporary'
    reservation_time TEXT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (zone_id) REFERENCES zones(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(event_id, zone_id, seat_number)
);

-- Insert default zones
INSERT INTO zones (name, price, total_seats, description) VALUES
    ('Партер', 800, 63, 'Партер - нижний ярус театра'),
    ('Амфитеатр', 1000, 49, 'Амфитеатр - основной зал с лучшим обзором'),
    ('Бельэтаж', 600, 50, 'Бельэтаж - верхний ярус театра'),
    ('Балкон', 1200, 35, 'Балкон - верхний ярус с ограниченным обзором');

-- Insert default admin user
INSERT INTO users (login, password, role) VALUES
    ('admin', 'admin123', 'admin'),
    ('manager', 'manager123', 'manager'),
    ('user', 'user123', 'user');

-- Insert sample events
INSERT INTO events (title, performers, venue, description, date, time, price, available_seats) VALUES
    ('Лебединое озеро', 'Большой театр', 'Большой театр', 'Классический балет в постановке Большого театра', date('now', '+1 day'), '19:00', 2000, 500),
    ('Евгений Онегин', 'Мариинский театр', 'Мариинский театр', 'Опера в постановке Мариинского театра', date('now', '+2 days'), '19:30', 1800, 450),
    ('Щелкунчик', 'Большой театр', 'Большой театр', 'Новогодний балет', date('now', '+3 days'), '18:00', 2200, 550),
    ('Кармен', 'Мариинский театр', 'Мариинский театр', 'Опера в постановке Мариинского театра', date('now', '+4 days'), '20:00', 1900, 480),
    ('Спящая красавица', 'Большой театр', 'Большой театр', 'Классический балет', date('now', '+5 days'), '19:00', 2100, 520);

-- Insert event zones for each event
INSERT INTO event_zones (event_id, zone_id, available_seats)
SELECT e.id, z.id, z.total_seats
FROM events e
CROSS JOIN zones z
WHERE e.id IN (SELECT id FROM events)
AND z.id IN (SELECT id FROM zones); 