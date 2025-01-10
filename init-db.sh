#!/bin/bash
set -ex

psql -v ON_ERROR_STOP=1 --username "$DB_USER" --dbname "$DB_NAME" <<-EOSQL
    CREATE SCHEMA postgis;
    ALTER DATABASE $DB_NAME SET search_path TO postgis, public;

    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
            CREATE EXTENSION postgis SCHEMA postgis;
        END IF;
    END
    \$\$;
EOSQL