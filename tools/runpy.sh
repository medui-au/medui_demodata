#!/bin/sh
# Run a Python tool from this folder inside the MedUI demo app image (it has pyodbc and ODBC Driver 18),
# connected as sa to the demo SQL Server only.
# Overrides: SQL_ENV (secrets file, default $HOME/.medui_demodata_sql.env), BPSQL_HOST (default bpsql2), DEMO_NETWORK, DEMO_IMAGE, BPSQL_HOST.
D=$(cd "$(dirname "$0")" && pwd)
ENVF=${SQL_ENV:-$HOME/.medui_demodata_sql.env}
exec docker run --rm --user 0 --network "${DEMO_NETWORK:-medui_demo_default}" -e BPSQL_HOST="${BPSQL_HOST:-bpsql2}" \
  --entrypoint python -v "$D":/work ${MEDUI_SQL_DIR:+-v "$MEDUI_SQL_DIR":/sql:ro} ${BPID_DIR:+-v "$BPID_DIR":/bpid:ro} -v "$ENVF":/secrets/dst.env:ro -w /work "${DEMO_IMAGE:-medui_demo-app}" -I "$@"
