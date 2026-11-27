"""Run every MedUI BP query (app/sql/*.sql) against the demo SQL Server, read-only, with each parameter set to NULL.

Catches missing tables, views and columns (which a compile-only check misses, because of deferred name resolution).
    MEDUI_SQL_DIR=/path/to/medui_os/app/sql tools/runpy.sh check_queries.py [--as-reader]
Exit status 1 if any query fails, other than those needing BPSDrugs (not part of the demo by choice).
"""
import os, re, sys, pathlib, pyodbc

kv = dict(l.strip().split('=', 1) for l in open('/secrets/dst.env') if '=' in l)
user, pw = ('sa', kv['MSSQL_SA_PASSWORD']) if '--as-reader' not in sys.argv else (kv['READER_USER'], kv['READER_PASSWORD'])
cn = pyodbc.connect("DRIVER={ODBC Driver 18 for SQL Server};SERVER=%s,1433;DATABASE=BPSPATIENTS;UID=%s;PWD=%s;Encrypt=yes;TrustServerCertificate=yes"
                    % (os.environ.get('BPSQL_HOST', 'bpsql2'), user, pw), autocommit=False)
TOKEN = re.compile(r"('(?:[^']|'')*')|(--[^\n]*)|(/\*.*?\*/)|(\?)|(:[A-Za-z_]\w*)", re.S)

def bind_nulls(sql):
    def sub(m):
        if m.group(1) or m.group(2) or m.group(3): return m.group(0)
        return 'NULL'
    return TOKEN.sub(sub, sql)

ok, bad, skipped = 0, [], []
for p in sorted(pathlib.Path('/sql').glob('*.sql')):
    sql = p.read_text(errors='ignore')
    if 'BPSDrugs' in sql:
        skipped.append(p.name); continue
    cur = cn.cursor()
    try:
        cur.execute(bind_nulls(sql))
        while True:
            if cur.description: cur.fetchall()
            if not cur.nextset(): break
        ok += 1
    except pyodbc.Error as e:
        bad.append((p.name, str(e.args[1] if len(e.args) > 1 else e)[:300]))
    finally:
        cn.rollback()
print(f"queries ok: {ok}, failed: {len(bad)}, skipped (BPSDrugs): {len(skipped)}")
for n, e in bad:
    print(f"  FAIL {n}: {re.sub(r'.*\\[SQL Server\\]', '', e)}")
sys.exit(1 if bad else 0)
