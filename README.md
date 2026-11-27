# medui_demodata: MedUI demo databases

Databases for MedUI demos and screen recordings, so MedUI can be shown without a Best Practice installation. **Every row is invented**; none comes from Best Practice's sample databases or from any real practice or patient.

- **Names:** all patients, staff, contacts, clinics and the practice (Sampleford Family Practice, in the fictional town of Sampleford, QLD 4999) are made up.
- **Numbers and contact details:**
  - Phone numbers are in the ranges Australia reserves for fiction.
  - Emails are at example.com.
  - Card and registration numbers are obviously fake (`DEMO…`, `MED-DEMO-…`, leading zeros).
- **Medicines:** generic names, with our own product IDs.
- **Codes:** conditions and vaccines carry the item and vaccine numbers that MedUI's own mappings read, so MedUI's disease profile and NIP check recognise them.

| Backup | Restores as | Size |
|---|---|---|
| `backups/BPSPATIENTS.bak` | BPSPATIENTS | 1.2 MB |
| `backups/BPSDocuments1.bak` | BPSDocuments1 | 0.6 MB |
| `backups/BPSDOCUMENTSINBOX.bak` | BPSDOCUMENTSINBOX | 0.6 MB |

The backups are compressed, copy-only and checksummed, made on **SQL Server 2022** (build 16.0.4315). They restore on SQL Server 2022 or newer, but not on 2019 or older. They hold **no user passwords**; the restore sets them from your secrets file.

## What's in it

- **Patients:** 43, of whom 40 are current: children, adults and over-75s, with matching storylines.
  - **Pathology:** 796 filed reports with 3,208 values, plus 60 unchecked inbox reports from the last two weeks.
  - **Visits:** 196, with progress notes, reasons and observations.
  - **History and medicines:** 169 history items and 311 medicines, 88 of them ceased with a reason.
  - **Vaccines:** 190, including the full childhood schedule.
  - **Letters:** 101 specialist letters as PDFs, and 29 outgoing referrals.
  - **Billing:** invoices, care-plan and health-assessment items, recalls and actions.
- **Users:** 9, with the same user numbers and BP groups MedUI expects.
  - Dr Imogen Thistlewood (practice owner, user 1) and Dr Callum Ravensworth (doctor, user 3) are the main doctors.
  - Rosalind Quenby is the nurse and Tessa Wyndham-Lowe the receptionist.
- **Bookings:** an appointment book for today and the next three weeks, plus a completed appointment for every past visit.
  - About 20 bookings each weekday: 12 with Dr Thistlewood and 8 with Dr Ravensworth.
  - 4 or 5 on Saturday mornings, with one of the two doctors, turn about. None on Sundays.
  - The 40 current patients fill the book, so each has about 8 bookings in the three weeks: more than a real patient would. Half are booked one weekday and the other half the next, so nobody is booked two weekdays running.

`docs/plausibility_checks.md` has the checks and their results.

## Restore

You need a SQL Server 2022 container, the MedUI demo app image (`medui_demo-app`, which the tools run in), and a mode-600 secrets file. The tools look for it at `~/.medui_demodata_sql.env`; set `SQL_ENV` to use another. It holds:

```
MSSQL_SA_PASSWORD=...
READER_USER=medui_demo_reader
READER_PASSWORD=...
DEMO_USER_PASSWORD=...
```

Then run:

```bash
restore/restore.sh medui_demodata-sql
```

The script then:

1. Checks the SHA-256 sums.
2. Restores the three databases. **It stops if any of them already exists.**
3. Creates or re-attaches the read-only login.
4. Gives every demo user `DEMO_USER_PASSWORD`.

Passwords go through environment variables or files, never on the command line.

- **Your set-up differs:** the tools assume the Docker network `medui_demo_default` and the server name `bpsql2`. Set `DEMO_NETWORK` and `BPSQL_HOST` if yours differ.
- **MedUI's `.env`:** set `BPSDB_HOST` to the server's name, `BPSDB_DATABASE=BPSPATIENTS`, `BPSDB_USER=medui_demo_reader` and `BPSDB_TRUST_SERVER_CERTIFICATE=true`. Type the reader password in yourself.

## Bring the dates up to today

The data is a snapshot as of 2026-11-07. `tools/refresh_dates.py` moves every date forward by whole weeks, dates of birth included:

- ages, weekdays and the links between records stay as they are;
- the appointment book is made again from today: bookings for today and the 20 days after it, with earlier ones removed. A given day has the same bookings whenever you refresh;
- the pathology reports' printed dates are rewritten to match.

It records its position in the database. Running it again in the same week moves no dates and only brings the appointment book forward to today. Do a dry run first, then the real one:

```bash
tools/runpy.sh refresh_dates.py --dry-run
```

```bash
tools/runpy.sh refresh_dates.py
```

## Checks

`tools/check_queries.py` runs every MedUI query against the databases (`MEDUI_SQL_DIR=<medui_os>/app/sql tools/runpy.sh check_queries.py --as-reader`). One query needs BPSDrugs, which isn't part of the demo, and is skipped. The maintainers' plausibility checks and their results are in `docs/plausibility_checks.md`.
## Before using with live BP

MedUI stores BP IDs in its own PostgreSQL with no record of which BP server they came from:

- **Patient IDs** on care plans, chats, transcripts, messages, documents, complaints, adverse events and workflow runs.
- **BP user IDs** on users.

If a MedUI install that has been used with this demo data is pointed at a live BP database, demo rows attach to whichever live patients and users happen to have the same IDs.

- **Keep demo and live installs separate,** and never point a demo install at live BP.
- **To reuse a demo install,** first delete its PostgreSQL and file storage by running `docker compose -p <demo project> down -v` in the demo install's folder only. In a live install's folder, the same command would wipe that install's data.

## Licence

The data and documentation are dedicated to the public domain under [CC0 1.0](LICENSE-CC0); the scripts are under the [Apache License 2.0](LICENSE). The databases are laid out as MedUI's queries expect. See [NOTICE](NOTICE), including what the licences don't cover.
