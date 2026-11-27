#!/bin/sh
# Run SQL (a file argument, or stdin) as sa on the demo SQL Server container, password via the environment only.
# Overrides: SQL_ENV (secrets file), DEMO_SQL_CONTAINER (default medui_demodata-sql).
ENVF=${SQL_ENV:-$HOME/.medui_demodata_sql.env}
PW=$(sed -n 's/^MSSQL_SA_PASSWORD=//p' "$ENVF")
if [ -n "$1" ]; then exec <"$1"; fi
SQLCMDPASSWORD="$PW" exec docker exec -i -e SQLCMDPASSWORD "${DEMO_SQL_CONTAINER:-medui_demodata-sql}" \
  /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -C -b -s '|' -W
