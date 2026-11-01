import sqlite3

def init_db(db_path):
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS clients (
        id            TEXT PRIMARY KEY,
        name          TEXT,
        email         TEXT,
        phone         TEXT,
        pan           TEXT,
        aadhaar       TEXT,
        gstin         TEXT,
        service       TEXT,
        status        TEXT DEFAULT 'new',
        flags         TEXT DEFAULT '[]',
        created_at    TEXT,
        updated_at    TEXT
    );
    CREATE TABLE IF NOT EXISTS documents (
        id            TEXT PRIMARY KEY,
        client_id     TEXT,
        doc_type      TEXT,
        filename      TEXT,
        filepath      TEXT,
        extracted     TEXT DEFAULT '{}',
        confidence    REAL DEFAULT 1.0,
        flags         TEXT DEFAULT '[]',
        uploaded_at   TEXT,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    );
    CREATE TABLE IF NOT EXISTS checklist (
        id            TEXT PRIMARY KEY,
        client_id     TEXT,
        doc_type      TEXT,
        required      INTEGER DEFAULT 1,
        received      INTEGER DEFAULT 0,
        doc_id        TEXT,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    );
    CREATE TABLE IF NOT EXISTS messages (
        id            TEXT PRIMARY KEY,
        client_id     TEXT,
        channel       TEXT,
        subject       TEXT,
        body          TEXT,
        status        TEXT DEFAULT 'draft',
        scheduled_at  TEXT,
        approved_by   TEXT,
        approved_at   TEXT,
        sent_at       TEXT,
        created_at    TEXT,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    );
    CREATE TABLE IF NOT EXISTS activity_log (
        id            TEXT PRIMARY KEY,
        client_id     TEXT,
        action        TEXT,
        detail        TEXT,
        created_at    TEXT
    );
    CREATE TABLE IF NOT EXISTS inbox_settings (
        id            INTEGER PRIMARY KEY CHECK (id = 1),
        provider      TEXT DEFAULT 'custom',
        host          TEXT,
        port          INTEGER DEFAULT 993,
        username      TEXT,
        password      TEXT,
        use_ssl       INTEGER DEFAULT 1,
        folder        TEXT DEFAULT 'INBOX',
        last_synced   TEXT,
        updated_at    TEXT
    );
    """)
    conn.commit()
    conn.close()
