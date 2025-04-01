#!/bin/bash

# Set proper permissions for database directory
chown -R www-data:www-data /usr/local/apache2/database
chmod 755 /usr/local/apache2/database

# Initialize database if it doesn't exist
DB_FILE="/usr/local/apache2/database/theater.db"
INIT_SQL="/usr/local/apache2/database/init.sql"

echo "Checking database initialization..."

if [ ! -f "$DB_FILE" ]; then
    echo "Database file does not exist, creating..."
    if [ -f "$INIT_SQL" ]; then
        echo "Found init.sql, initializing database..."
        sqlite3 "$DB_FILE" < "$INIT_SQL"
        if [ $? -eq 0 ]; then
            echo "Database initialized successfully"
        else
            echo "Error initializing database"
            exit 1
        fi
    else
        echo "Error: init.sql not found at $INIT_SQL"
        exit 1
    fi
else
    echo "Database file already exists"
fi

# Set proper permissions for the database file
chown www-data:www-data "$DB_FILE"
chmod 644 "$DB_FILE"

# Verify database tables
echo "Verifying database tables..."
for table in users events zones event_zones orders cart; do
    if sqlite3 "$DB_FILE" "SELECT name FROM sqlite_master WHERE type='table' AND name='$table';" | grep -q "$table"; then
        echo "Table '$table' exists"
    else
        echo "Warning: Table '$table' does not exist!"
        echo "Reinitializing database..."
        rm -f "$DB_FILE"
        sqlite3 "$DB_FILE" < "$INIT_SQL"
        chown www-data:www-data "$DB_FILE"
        chmod 644 "$DB_FILE"
        break
    fi
done

# Execute the main container command
exec "$@" 