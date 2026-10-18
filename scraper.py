import hashlib
import json
import re
import sqlite3
from datetime import datetime
from urllib.parse import urlparse, urlunparse
import feedparser
import trafilatura
from bs4 import BeautifulSoup

DB_PATH = "/opt/explainer-service/data/news.db"

RSS_FEEDS = [
    {
        "url": "https://www.moneycontrol.com/rss/MCtopnews.xml",
        "category": "market"
    },
    {
        "url": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
        "category": "economy"
    },
    {
        "url": "https://www.livemint.com/rss/money",
        "category": "personal-finance"
    }
]

# Strict, non-overlapping calculator mapping
CALCULATOR_RULES = [
    {
        "calc": "inflation-calculator",
        "keywords": ["da hike", "dearness allowance", "dearness relief", "pay commission", "cpi inflation", "retail inflation"],
        "related": ["sip-investment", "fd-rd-calculator"]
    },
    {
        "calc": "in-hand-salary",
        "keywords": ["take-home salary", "ctc", "epf", "gratuity", "new tax regime", "section 115bac", "tds on salary"],
        "related": ["inflation-calculator"]
    },
    {
        "calc": "sip-investment",
        "keywords": ["mutual fund", "sip", "equity fund", "nifty", "sensex", "nav", "portfolio rebalance", "index fund"],
        "related": ["inflation-calculator", "fd-rd-calculator"]
    },
    {
        "calc": "home-loan-prepayment",
        "keywords": ["home loan", "repo rate", "emi", "lending rate", "rbi mpc", "mortgage", "prepayment penalty"],
        "related": ["in-hand-salary"]
    },
    {
        "calc": "gold-jewelry-bill",
        "keywords": ["gold price", "sovereign gold bond", "sgb", "bullion", "silver price", "making charges", "hallmark gold"],
        "related": ["sip-investment"]
    },
    {
        "calc": "electricity-bill",
        "keywords": ["power tariff", "electricity bill", "discom", "power consumption", "units consumed"],
        "related": ["solar-rooftop"]
    },
    {
        "calc": "gst-inclusive-price-calculator",
        "keywords": ["gst rate", "indirect tax", "gst council", "input tax credit", "e-way bill"],
        "related": ["wholesale-profit-margin"]
    }
]

def clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', '')).rstrip('/')

def get_url_hash(url: str) -> str:
    return hashlib.sha256(clean_url(url).encode('utf-8')).hexdigest()

def is_already_scraped(url_hash: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM explainers WHERE url_hash = ? LIMIT 1", (url_hash,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    slug = re.sub(r'[\s_-]+', '-', text).strip('-')
    return slug[:110] if slug else "explainer"

def detect_calculators(text: str):
    lower = text.lower()
    for rule in CALCULATOR_RULES:
        if any(keyword in lower for keyword in rule["keywords"]):
            return rule["calc"], rule["related"]
    return None, []

def extract_full_article(url: str) -> str:
    """Extracts main editorial text using trafilatura, filtering out ads/nav."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            extracted = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                no_fallback=False
            )
            if extracted and len(extracted.strip()) > 500:
                return extracted.strip()
    except Exception as e:
        print(f"Trafilatura extraction failed for {url}: {e}")
    return ""

def save_explainer(data: dict) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO explainers (
            slug, title, summary, content, category,
            primary_calculator, related_calculators, source_reference,
            url_hash, published_at, created_at, status, ai_transformed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'pending', 0)
    """, (
        data["slug"],
        data["title"],
        data["summary"],
        data["content"],
        data["category"],
        data["primary_calculator"],
        json.dumps(data["related_calculators"]),
        data["source_reference"],
        data["url_hash"],
        data["published_at"]
    ))
    inserted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return inserted

def run_scraper():
    scraped_at = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0530")
    print(f"--- Starting Upgraded Scraper Run at {scraped_at} ---")
    new_count = 0

    for feed_info in RSS_FEEDS:
        feed_url = feed_info["url"]
        category = feed_info["category"]
        print(f"\nChecking feed: {feed_url}")

        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"Failed to parse feed {feed_url}: {e}")
            continue

        for entry in feed.entries[:10]:
            raw_url = entry.get("link", "")
            if not raw_url:
                continue

            cleaned = clean_url(raw_url)
            url_hash = get_url_hash(cleaned)

            if is_already_scraped(url_hash):
                continue

            title = entry.get("title", "").strip()
            if not title:
                continue

            raw_summary = entry.get("summary", "")
            summary = BeautifulSoup(raw_summary, "html.parser").get_text(strip=True) if raw_summary else ""

            # Fetch the actual editorial article body
            full_text = extract_full_article(cleaned)

            # QUALITY GATE: If full text extraction failed or was paywalled (< 500 chars), skip it.
            # Do not pass thin snippets to LLM.
            if not full_text:
                print(f"[REJECTED - THIN CONTENT] {title[:50]} (Could not extract main body)")
                continue

            primary_calc, related_calcs = detect_calculators(f"{title} {summary} {full_text[:400]}")
            
            # If no financial calculator logically pairs with this news item, skip or mark as generic
            slug = f"{slugify(title)}-{url_hash[:8]}"

            data = {
                "slug": slug,
                "title": title,
                "summary": summary[:300] if summary else title,
                "content": full_text,  # Clean, 500-1500+ character body text
                "category": category,
                "primary_calculator": primary_calc,
                "related_calculators": related_calcs,
                "source_reference": cleaned,
                "url_hash": url_hash,
                "published_at": scraped_at
            }

            if save_explainer(data):
                calc_label = f" [Linked: {primary_calc}]" if primary_calc else " [General]"
                print(f"[SAVED]{calc_label} {title[:60]}... ({len(full_text)} chars)")
                new_count += 1
            else:
                print(f"[SKIPPED] Duplicate entry: {title[:40]}")

    print(f"\n--- Finished: {new_count} high-quality explainers ready for synthesis ---")

if __name__ == "__main__":
    run_scraper()
