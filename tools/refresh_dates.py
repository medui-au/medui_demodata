"""Move the whole demo record forward in time so the inbox, appointments, recalls and recent visits look current.

Every date in BPSPATIENTS, BPSDocuments1 and BPSDOCUMENTSINBOX moves by the same whole number of weeks, so:
- weekdays stay weekdays;
- each item keeps its age relative to the patient, because DOBs move too and ages stay as they were;
- links stay intact (a result-review visit still follows its pathology batch, and billing still matches its visit).

Exceptions:
- The appointment book (APPOINTMENTS RECORDID below 2001) is made again, not moved: bookings for the target day and the
  20 days after it, about 20 each weekday, 4 or 5 on Saturday mornings, none on Sundays (bookings.py). A given day has
  the same bookings whenever this runs. The completed visit appointments (RECORDID 2001 and up) move by weeks like
  everything else.
- Year-only numbers (history year, smoking, alcohol, occupation) move by the change in calendar year.
- Dates written inside the pathology reports ("Collected: dd/mm/yyyy", lab ref "DPyy-") are rewritten to match.
- Left alone: 1900-01-01 placeholders and far-future sentinels.

The current position is kept in the BPSPATIENTS extended property MedUIDemoAnchor (2026-11-07 when the backup was
made). Running again in the same week moves no dates, and only brings the appointment book forward to the target day.

Usage (as sa on the demo server only; see runpy.sh):
    runpy.sh refresh_dates.py              # move to today
    runpy.sh refresh_dates.py --dry-run    # show what would change, then roll back
    runpy.sh refresh_dates.py --to 2027-03-01
"""
import argparse, datetime as dt, io, os, re, sys, zipfile
import pyodbc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # runpy.sh starts Python with -I
from bookings import SYN_APPT_LT, make_bookings

SNAPSHOT = dt.date(2026, 11, 7)      # anchor of the published backup
DBS = ('BPSPATIENTS', 'BPSDocuments1', 'BPSDOCUMENTSINBOX')
SYN_PATH = 1                          # every pathology report is generated
STAMP_LO, STAMP_HI = '1900-01-01', '1900-01-01'   # no install stamps in the generated data
PROP = 'MedUIDemoAnchor'

ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
ap.add_argument('--to', type=dt.date.fromisoformat, default=dt.date.today(), help='target date (default today)')
ap.add_argument('--dry-run', action='store_true', help='make the changes inside a transaction, report, then roll back')
a = ap.parse_args()

kv = dict(l.strip().split('=', 1) for l in open(os.environ.get('SQL_ENV_FILE', '/secrets/dst.env')) if '=' in l and not l.startswith('#'))
host = os.environ.get('BPSQL_HOST', 'bpsql2')
cn = pyodbc.connect("DRIVER={ODBC Driver 18 for SQL Server};SERVER=%s,1433;DATABASE=BPSPATIENTS;UID=sa;PWD=%s;Encrypt=yes;"
                    "TrustServerCertificate=yes" % (host, kv['MSSQL_SA_PASSWORD']), autocommit=False)
cur = cn.cursor()
# The public demo backups carry only the columns MedUI reads (tools/columns.txt), so a column used
# here may be absent: has() says whether this database has it.
_present = {(t.upper(), c.upper()) for t, c in cur.execute("SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS").fetchall()}
def has(t, c): return (t.upper(), c.upper()) in _present

r = cur.execute("SELECT CAST(value AS nvarchar(20)) FROM sys.extended_properties WHERE class = 0 AND name = ?", PROP).fetchone()
anchor = dt.date.fromisoformat(r[0]) if r else SNAPSHOT
weeks = round((a.to - anchor).days / 7)
days = weeks * 7
new_anchor = anchor + dt.timedelta(days=days)
years = new_anchor.year - anchor.year
print(f"anchor {anchor} -> {new_anchor} (target {a.to}): {days:+d} days ({weeks:+d} weeks), year-only values {years:+d}")


def rebook():
    """The appointment book from the target day: out with the old bookings, in with three weeks of new ones.

    After the dates have moved, so the patients' ages are the ones the book is made for.
    """
    patients = [(pid, dob.date()) for pid, dob in cur.execute(
        "SELECT INTERNALID, DOB FROM dbo.PATIENTS WHERE PATIENTSTATUS IN (1, 2) AND RECORDSTATUS = 1"
        + (" AND DATEOFDEATH IS NULL" if has('PATIENTS', 'DATEOFDEATH') else ''))]
    book = make_bookings(patients, a.to)
    cols = cur.execute("SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
                       "WHERE TABLE_NAME = 'APPOINTMENTS' ORDER BY ORDINAL_POSITION").fetchall()
    blank = lambda typ, nul: None if nul == 'YES' else dt.datetime(1900, 1, 1) if 'date' in typ else '' if 'char' in typ else 0
    cur.execute("DELETE FROM dbo.APPOINTMENTS WHERE RECORDID < ?", SYN_APPT_LT)
    gone = cur.rowcount
    if book:
        cur.executemany(f"INSERT INTO dbo.APPOINTMENTS ({', '.join('[' + c + ']' for c, _, _ in cols)}) VALUES ({', '.join('?' * len(cols))})",
                        [tuple(r.get(c, blank(typ, nul)) for c, typ, nul in cols) for r in book])
    last = max(r['APPOINTMENTDATE'] for r in book).date() if book else a.to
    print(f"appointment book: {gone} old bookings out, {len(book)} in, {a.to} to {last} ({len(patients)} current patients)")


if days == 0:
    rebook()
    if a.dry_run:
        cn.rollback(); print("No dates to move. DRY RUN: rolled back, nothing changed.")
    else:
        cn.commit(); print("No dates to move: the appointment book is up to date.")
    sys.exit(0)

def shifted(s, fmt):
    return (dt.datetime.strptime(s, fmt) + dt.timedelta(days=days)).strftime(fmt)

# 1. every date column in every base table
total = 0
for db in DBS:
    cols = cur.execute(f"""SELECT c.TABLE_NAME, c.COLUMN_NAME FROM [{db}].INFORMATION_SCHEMA.COLUMNS c
        JOIN [{db}].INFORMATION_SCHEMA.TABLES t ON t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_TYPE = 'BASE TABLE'
        WHERE c.TABLE_SCHEMA = 'dbo' AND c.DATA_TYPE IN ('date', 'datetime', 'datetime2', 'smalldatetime', 'datetimeoffset')""").fetchall()
    for t, c in cols:
        cur.execute(f"UPDATE [{db}].dbo.[{t}] SET [{c}] = DATEADD(day, ?, [{c}]) WHERE [{c}] >= '1901-01-01' AND [{c}] < '2100-01-01'"
                    f" AND NOT ([{c}] >= '{STAMP_LO}' AND [{c}] < '{STAMP_HI}')", days)
        total += max(cur.rowcount, 0)
print(f"date values moved: {total}")

# 2. the appointment book: made again from the target day (the DOBs have moved by now)
rebook()

# 3. numbers that hold years
cur.execute("""UPDATE h SET YEAR = YEAR(x.d), MONTH = MONTH(x.d), DAY = CASE WHEN h.DAY BETWEEN 1 AND 31 THEN DAY(x.d) ELSE h.DAY END
    FROM dbo.PASTHISTORY h CROSS APPLY (SELECT DATEADD(day, ?, DATEFROMPARTS(h.YEAR, h.MONTH, CASE WHEN h.DAY BETWEEN 1 AND 28 THEN h.DAY ELSE 1 END)) d) x
    WHERE h.YEAR BETWEEN 1801 AND 2100 AND h.MONTH BETWEEN 1 AND 12""", days)
n = cur.rowcount
if years:
    cur.execute("UPDATE dbo.PASTHISTORY SET YEAR = YEAR + ? WHERE YEAR BETWEEN 1801 AND 2100 AND NOT (MONTH BETWEEN 1 AND 12)", years); n += cur.rowcount
    for t, cs in (('TOBACCO', ('YEARSTARTED', 'PASTSTARTED', 'PASTSTOPPED')), ('ALCOHOL', ('YEARSTARTED', 'YEARSTOPPED')),
                  ('OCCUPATIONHISTORY', ('YEARSTARTED', 'YEARSTOPPED'))):
        for c in (c for c in cs if has(t, c)):
            cur.execute(f"UPDATE dbo.{t} SET {c} = {c} + ? WHERE {c} BETWEEN 1801 AND 2100", years); n += cur.rowcount
print(f"year numbers moved: {n}")

# 4. dates written inside the synthetic pathology reports
DMY = re.compile(r'\b(\d\d/\d\d/\d{4})\b')
def fix_text(s):
    s = DMY.sub(lambda m: shifted(m.group(1), '%d/%m/%Y'), s)
    rep = re.search(r'Reported: (\d\d/\d\d/(\d{4}))', s)
    if rep: s = re.sub(r'\bDP\d\d-', f'DP{rep.group(2)[2:]}-', s)
    return s, (rep.group(2)[2:] if rep else None)
def fix_ref(ref, yy): return re.sub(r'^DP\d\d-', f'DP{yy}-', ref) if (ref and yy) else ref

k = 0
def refcol(t): return 'PROVIDERREFERENCE' if has(t, 'PROVIDERREFERENCE') else 'NULL'
def setref(t): return ', PROVIDERREFERENCE = ?' if has(t, 'PROVIDERREFERENCE') else ''
def refarg(t, ref, yy): return [fix_ref(ref, yy)] if has(t, 'PROVIDERREFERENCE') else []
for rid, hdr, ref in cur.execute(f"SELECT REPORTID, CAST(REPORTHEADER AS varchar(max)), {refcol('INCOMINGREPORTS')} FROM dbo.INCOMINGREPORTS WHERE REPORTID >= ?", SYN_PATH).fetchall():
    new, yy = fix_text(hdr or '')
    cur.execute(f"UPDATE dbo.INCOMINGREPORTS SET REPORTHEADER = ?{setref('INCOMINGREPORTS')} WHERE REPORTID = ?", new, *refarg('INCOMINGREPORTS', ref, yy), rid); k += 1
for rid, blob, ref in cur.execute(f"SELECT REPORTID, REPORTHEADER, {refcol('INVESTIGATIONS')} FROM dbo.INVESTIGATIONS WHERE REPORTID >= ?", SYN_PATH).fetchall():
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        name = z.namelist()[0]; text = z.read(name).decode('latin-1')
    new, yy = fix_text(text)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z: z.writestr(name, new.encode('latin-1'))
    cur.execute(f"UPDATE dbo.INVESTIGATIONS SET REPORTHEADER = ?{setref('INVESTIGATIONS')} WHERE REPORTID = ?", buf.getvalue(), *refarg('INVESTIGATIONS', ref, yy), rid); k += 1
print(f"synthetic report headers rewritten: {k}")

# 5. remember where we are
fn = 'sp_updateextendedproperty' if r else 'sp_addextendedproperty'
cur.execute(f"EXEC {fn} @name = ?, @value = ?", PROP, new_anchor.isoformat())

s = cur.execute("""SELECT (SELECT MIN(APPOINTMENTDATE) FROM dbo.APPOINTMENTS WHERE RECORDID < ?), (SELECT MAX(APPOINTMENTDATE) FROM dbo.APPOINTMENTS WHERE RECORDID < ?),
    (SELECT MAX(COLLECTIONDATE) FROM dbo.INCOMINGREPORTS""" + (" WHERE CHECKSTATUS = 0" if has('INCOMINGREPORTS', 'CHECKSTATUS') else '') + """), (SELECT MAX(VISITDATE) FROM dbo.VISITS WHERE RECORDSTATUS = 1)""", SYN_APPT_LT, SYN_APPT_LT).fetchone()
print(f"now: bookings {s[0]:%Y-%m-%d} to {s[1]:%Y-%m-%d}; newest inbox collection {s[2]:%Y-%m-%d}; newest visit {s[3]:%Y-%m-%d}")
if a.dry_run:
    cn.rollback(); print("DRY RUN: rolled back, nothing changed.")
else:
    cn.commit(); print(f"Committed. Anchor is now {new_anchor}.")
