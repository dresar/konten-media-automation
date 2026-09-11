import json
import os
import re
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "news_database.db")

CATEGORIES = [
    {
        "scope": "LOKAL",
        "category": "KEAMANAN_SIBER_INDONESIA",
        "label": "Keamanan Siber & Kasus Pembobolan Data Indonesia",
        "keywords": "kebocoran data, malware APK modus kurir/undangan, ransomware, phishing m-banking, BSSN, Kominfo, SIM swap, pinjol ilegal"
    },
    {
        "scope": "GLOBAL",
        "category": "GADGET_SMARTPHONE_GLOBAL",
        "label": "Gadget, Smartphone & Wearable Masa Depan",
        "keywords": "Apple iPhone, iOS, Samsung Galaxy, Google Pixel, foldable phone, kamera periskop, baterai silikon karbon, smart watch"
    },
    {
        "scope": "LOKAL",
        "category": "TELCO_INTERNET_INDONESIA",
        "label": "Telekomunikasi, Internet & Regulasi Digital Indonesia",
        "keywords": "Starlink Indonesia, jaringan 5G Telkomsel/Indosat/XL, satelit Satria, aturan IMEI, Kominfo, blokir situs, fiber optic"
    },
    {
        "scope": "GLOBAL",
        "category": "CELAH_KEAMANAN_GLOBAL",
        "label": "Celah Keamanan Global & Zero-Day Alert",
        "keywords": "zero-day exploit, ransomware global, bug kritis Chrome/Windows, spionase siber, peretasan cloud, hacker group"
    },
    {
        "scope": "LOKAL",
        "category": "FINTECH_STARTUP_INDONESIA",
        "label": "Fintech, Perbankan Digital & Startup Indonesia",
        "keywords": "QRIS antar-negara ASEAN, BI-Fast, dompet digital, bank digital, startup teknologi, keamanan transaksi e-wallet"
    },
    {
        "scope": "GLOBAL",
        "category": "HARDWARE_SEMICONDUCTOR",
        "label": "Hardware, GPU & Chipset Komputasi",
        "keywords": "Nvidia GPU, chip TSMC 2nm/3nm, Intel vs AMD, prosesor Snapdragon X Elite, revolusi memori RAM, quantum processor"
    },
    {
        "scope": "GLOBAL",
        "category": "ROBOTIK_SATELLITE_SPACE",
        "label": "Robotik, Humanoid & Teknologi Eksplorasi",
        "keywords": "humanoid robot Tesla Optimus, Boston Dynamics, Neuralink, SpaceX satelit, mobil otonom autopilot, drone canggih"
    },
    {
        "scope": "GLOBAL",
        "category": "SOFTWARE_OS_BROWSER",
        "label": "Sistem Operasi, Software & Browser",
        "keywords": "pembaruan Windows 11, Google Chrome update, Android OS update, Open Source tools, browser privacy, Linux kernel"
    }
]


def get_connection(db_path=DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DB_PATH):
    with get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,
                category TEXT NOT NULL,
                topic TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                hook TEXT,
                points TEXT,
                tips TEXT,
                caption TEXT,
                hashtags TEXT,
                prompt_image TEXT,
                raw_image_path TEXT,
                processed_image_path TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                tiktok_mode TEXT DEFAULT 'now',
                tiktok_post_url TEXT,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                published_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_topic ON news_history(topic)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_status ON news_history(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_scope ON news_history(scope)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_created ON news_history(created_at)")
        conn.commit()


def get_blacklist_topics(limit=40, db_path=DB_PATH):
    init_db(db_path)
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT topic, title FROM news_history ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        topics = []
        for r in rows:
            if r["topic"]:
                topics.append(r["topic"])
            if r["title"]:
                topics.append(r["title"])
        return list(dict.fromkeys(topics))


def get_next_target_category(db_path=DB_PATH):
    init_db(db_path)
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT scope, category FROM news_history ORDER BY id DESC LIMIT 4")
        recent = cur.fetchall()

    if not recent:
        return CATEGORIES[0]

    last_scope = recent[0]["scope"]
    recent_cats = [r["category"] for r in recent]
    next_scope = "GLOBAL" if last_scope == "LOKAL" else "LOKAL"

    candidates = [c for c in CATEGORIES if c["scope"] == next_scope and c["category"] not in recent_cats]
    if not candidates:
        candidates = [c for c in CATEGORIES if c["scope"] == next_scope]
    if not candidates:
        candidates = CATEGORIES

    return candidates[0]


def is_duplicate(topic, title, db_path=DB_PATH):
    init_db(db_path)
    norm_topic = re.sub(r"[^\w\s]", "", topic.lower()).strip()
    norm_title = re.sub(r"[^\w\s]", "", title.lower()).strip()
    topic_words = set(w for w in norm_topic.split() if len(w) > 3)

    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT topic, title FROM news_history")
        rows = cur.fetchall()
        for r in rows:
            existing_t = re.sub(r"[^\w\s]", "", (r["topic"] or "").lower()).strip()
            existing_title = re.sub(r"[^\w\s]", "", (r["title"] or "").lower()).strip()

            if norm_topic == existing_t or norm_title == existing_title:
                return True

            existing_words = set(w for w in existing_t.split() if len(w) > 3)
            if topic_words and existing_words:
                overlap = topic_words.intersection(existing_words)
                if len(overlap) >= 3 and len(overlap) / max(len(topic_words), len(existing_words)) > 0.65:
                    return True

    return False


def insert_news(scope, category, topic, title, hook, points, tips, caption, hashtags, prompt_image, db_path=DB_PATH):
    init_db(db_path)
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO news_history (
                scope, category, topic, title, hook, points, tips, caption, hashtags, prompt_image, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (
            scope,
            category,
            topic,
            title,
            hook,
            json.dumps(points, ensure_ascii=False) if isinstance(points, (list, dict)) else str(points),
            tips,
            caption,
            hashtags,
            prompt_image,
            datetime.now().isoformat()
        ))
        conn.commit()
        return cur.lastrowid


def update_news_status(news_id, status, raw_image_path=None, processed_image_path=None, tiktok_mode="now", tiktok_post_url=None, db_path=DB_PATH):
    init_db(db_path)
    with get_connection(db_path) as conn:
        fields = ["status = ?"]
        vals = [status]
        if raw_image_path:
            fields.append("raw_image_path = ?")
            vals.append(raw_image_path)
        if processed_image_path:
            fields.append("processed_image_path = ?")
            vals.append(processed_image_path)
        if tiktok_mode:
            fields.append("tiktok_mode = ?")
            vals.append(tiktok_mode)
        if tiktok_post_url:
            fields.append("tiktok_post_url = ?")
            vals.append(tiktok_post_url)
        if status == "PUBLISHED":
            fields.append("published_at = ?")
            vals.append(datetime.now().isoformat())

        vals.append(news_id)
        query = f"UPDATE news_history SET {', '.join(fields)} WHERE id = ?"
        conn.execute(query, vals)
        conn.commit()


def get_stats(db_path=DB_PATH):
    init_db(db_path)
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) as total, count(CASE WHEN status='PUBLISHED' THEN 1 END) as published FROM news_history")
        row = cur.fetchone()
        cur.execute("SELECT scope, count(*) as count FROM news_history GROUP BY scope")
        scopes = {r["scope"]: r["count"] for r in cur.fetchall()}
        cur.execute("SELECT category, count(*) as count FROM news_history GROUP BY category")
        categories = {r["category"]: r["count"] for r in cur.fetchall()}
        return {
            "total": row["total"],
            "published": row["published"],
            "by_scope": scopes,
            "by_category": categories
        }
