#!/usr/bin/env bash
# Create a dedicated login role and database, then install PostGIS.
# The app never uses the postgres superuser. Run this in your terminal; sudo asks for your password.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if [[ ! -f .env ]]; then
  python3 - <<'PY'
import secrets
from pathlib import Path
password = secrets.token_hex(24)
Path(".env").write_text(
    "\n".join(
        [
            "APP_ENV=development",
            "POSTGRES_HOST=127.0.0.1",
            "POSTGRES_PORT=5432",
            "POSTGRES_DB=ies_app_db",
            "POSTGRES_USER=ies_app",
            f"POSTGRES_PASSWORD={password}",
            "POSTGRES_SSLMODE=prefer",
            "DB_ECHO=false",
            "",
        ]
    )
)
Path(".env").chmod(0o600)
PY
  echo "Wrote .env with a new database password. It is not printed."
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

if [[ ! "$POSTGRES_USER" =~ ^[a-z_][a-z0-9_]*$ ]] || [[ ! "$POSTGRES_DB" =~ ^[a-z_][a-z0-9_]*$ ]]; then
  echo "POSTGRES_USER and POSTGRES_DB must be simple lowercase identifiers." >&2
  exit 1
fi
if [[ -z "${POSTGRES_PASSWORD}" ]]; then
  echo "POSTGRES_PASSWORD is empty in .env." >&2
  exit 1
fi

sql_password="${POSTGRES_PASSWORD//\'/\'\'}"

sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${POSTGRES_USER}') THEN
    CREATE ROLE ${POSTGRES_USER}
      LOGIN
      PASSWORD '${sql_password}'
      NOSUPERUSER
      NOCREATEDB
      NOCREATEROLE;
  ELSE
    ALTER ROLE ${POSTGRES_USER}
      WITH LOGIN
      PASSWORD '${sql_password}'
      NOSUPERUSER
      NOCREATEDB
      NOCREATEROLE;
  END IF;
END
\$\$;

SELECT format('CREATE DATABASE %I OWNER %I', '${POSTGRES_DB}', '${POSTGRES_USER}')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '${POSTGRES_DB}')
\gexec

REVOKE ALL ON DATABASE ${POSTGRES_DB} FROM PUBLIC;
GRANT CONNECT, TEMP ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d "$POSTGRES_DB" <<SQL
CREATE EXTENSION IF NOT EXISTS postgis;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO ${POSTGRES_USER};
SQL

echo "Database ${POSTGRES_DB} is ready for role ${POSTGRES_USER}. PostGIS is installed."
