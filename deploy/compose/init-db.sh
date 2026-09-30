#!/bin/sh
set -eu
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -v ON_ERROR_STOP=1 -v app_password="$TDR_DB_PASSWORD" <<'SQL'
CREATE ROLE tdr_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD :'app_password';
SQL
