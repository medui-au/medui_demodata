-- Restore the three MedUI demo databases from /var/opt/mssql/backup inside the SQL Server container.
-- Run with sqlcmd as sa. Stops if a database of the same name already exists (no REPLACE).
-- Needs SQL Server 2022 or newer: a 2022 backup will not restore on 2019 or older.
:on error exit
IF DB_ID('BPSPATIENTS') IS NOT NULL OR DB_ID('BPSDocuments1') IS NOT NULL OR DB_ID('BPSDOCUMENTSINBOX') IS NOT NULL
    THROW 50001, 'A BPS demo database already exists on this server. Drop it first if you really mean to replace it.', 1;
RESTORE DATABASE BPSPATIENTS FROM DISK = '/var/opt/mssql/backup/BPSPATIENTS.bak' WITH CHECKSUM,
    MOVE 'BPSPATIENTS' TO '/var/opt/mssql/data/BPSPATIENTS.mdf', MOVE 'BPSPATIENTS_log' TO '/var/opt/mssql/data/BPSPATIENTS_log.ldf';
RESTORE DATABASE BPSDocuments1 FROM DISK = '/var/opt/mssql/backup/BPSDocuments1.bak' WITH CHECKSUM,
    MOVE 'BPSDocuments1' TO '/var/opt/mssql/data/BPSDocuments1.mdf', MOVE 'BPSDocuments1_log' TO '/var/opt/mssql/data/BPSDocuments1_log.ldf';
RESTORE DATABASE BPSDOCUMENTSINBOX FROM DISK = '/var/opt/mssql/backup/BPSDOCUMENTSINBOX.bak' WITH CHECKSUM,
    MOVE 'BPSDOCUMENTSINBOX' TO '/var/opt/mssql/data/BPSDOCUMENTSINBOX.mdf', MOVE 'BPSDOCUMENTSINBOX_log' TO '/var/opt/mssql/data/BPSDOCUMENTSINBOX_log.ldf';
GO
