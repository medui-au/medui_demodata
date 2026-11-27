#!/usr/bin/env bash
# Restore the demo databases into a running SQL Server 2022 container and create the read-only login.
# Usage: restore/restore.sh [container]   (default medui_demodata-sql)
# Reads MSSQL_SA_PASSWORD, READER_USER, READER_PASSWORD and DEMO_USER_PASSWORD from ~/.medui_demodata_sql.env (mode 600),
# or SQL_ENV if set. The backups hold no user passwords: the last step sets them (needs the MedUI demo app image).
set -euo pipefail
C=${1:-medui_demodata-sql}
HERE=$(cd "$(dirname "$0")/.." && pwd)
ENVF=${SQL_ENV:-$HOME/.medui_demodata_sql.env}
MSSQL_SA_PASSWORD=$(sed -n "s/^MSSQL_SA_PASSWORD=//p" "$ENVF"); READER_USER=$(sed -n "s/^READER_USER=//p" "$ENVF")
READER_PASSWORD=$(sed -n "s/^READER_PASSWORD=//p" "$ENVF"); SQLCMDPASSWORD=$MSSQL_SA_PASSWORD; export READER_USER READER_PASSWORD SQLCMDPASSWORD
(cd "$HERE/backups" && sha256sum -c SHA256SUMS)
docker exec -u mssql "$C" mkdir -p /var/opt/mssql/backup
for d in BPSPATIENTS BPSDocuments1 BPSDOCUMENTSINBOX; do
  docker cp "$HERE/backups/$d.bak" "$C:/var/opt/mssql/backup/$d.bak"
  docker exec -u 0 "$C" chown mssql /var/opt/mssql/backup/$d.bak
done
SQ=(docker exec -i -e SQLCMDPASSWORD -e READER_USER -e READER_PASSWORD "$C" /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -C -b)
"${SQ[@]}" < "$HERE/restore/restore.sql"
"${SQ[@]}" < "$HERE/restore/create_reader.sql"
echo "Restored. Point MedUI's .env at this server: BPSDB_DATABASE=BPSPATIENTS, BPSDB_USER=$READER_USER."
echo "Setting the demo users' password:"; SQL_ENV="$ENVF" "$HERE/tools/runpy.sh" set_user_password.py || echo "Set DEMO_USER_PASSWORD, then run tools/runpy.sh set_user_password.py"
echo "To bring the dates up to today: tools/runpy.sh refresh_dates.py --dry-run, then without --dry-run."
