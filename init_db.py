import sqlite3

DB_PATH = "/opt/explainer-service/data/news.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS explainers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT DEFAULT 'personal-finance',
        primary_calculator TEXT,
        related_calculators TEXT,
        source_reference TEXT,
        url_hash TEXT UNIQUE NOT NULL,
        published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_explainers_url_hash ON explainers(url_hash);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_explainers_slug ON explainers(slug);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_explainers_calc ON explainers(primary_calculator);")
    
    conn.commit()
    conn.close()
    print("Explainers table schema successfully initialized.")

if __name__ == "__main__":
    init_db()
