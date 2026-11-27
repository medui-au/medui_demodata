"""Give every demo BP user the demo password (DEMO_USER_PASSWORD in the secrets file), as salt + SHA-256 in the format
MedUI checks. Changes only USERS.PASSWORD and USERS.PasswordSalt. Demo SQL Server only, as sa:
    tools/runpy.sh set_user_password.py
"""
import hashlib, os, secrets, sys, pyodbc
kv = dict(l.strip().split('=', 1) for l in open('/secrets/dst.env') if '=' in l and not l.startswith('#'))
pw = kv.get('DEMO_USER_PASSWORD', '').strip()
if not pw:
    sys.exit('DEMO_USER_PASSWORD is blank in the secrets file: type the demo password in there first.')
cn = pyodbc.connect("DRIVER={ODBC Driver 18 for SQL Server};SERVER=%s,1433;DATABASE=BPSPATIENTS;UID=sa;PWD=%s;Encrypt=yes;TrustServerCertificate=yes"
                    % (os.environ.get('BPSQL_HOST', 'bpsql2'), kv['MSSQL_SA_PASSWORD']), autocommit=False)
cur = cn.cursor()
n = 0
for (uid,) in cur.execute("SELECT USERID FROM dbo.USERS").fetchall():
    salt = secrets.token_hex(16)
    cur.execute("UPDATE dbo.USERS SET PasswordSalt = ?, PASSWORD = ? WHERE USERID = ?", salt, hashlib.sha256((pw + salt).encode()).hexdigest().upper(), uid)
    n += 1
cn.commit()
print(f"password set for {n} users")
