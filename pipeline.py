import sys
import time
import subprocess
import sqlite3

DB_PATH = "/opt/explainer-service/data/news.db"

def run_step(step_name, command):
    print(f"\n==========================================")
    print(f"▶ Starting: {step_name}")
    print(f"==========================================")
    start = time.time()
    
    result = subprocess.run([sys.executable] + command)
    duration = time.time() - start
    
    if result.returncode != 0:
        print(f"✖ {step_name} failed with exit code {result.returncode}")
        return False
        
    print(f"✔ {step_name} finished in {duration:.1f}s")
    return True

def get_pending_count():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM explainers WHERE ai_transformed = 0")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"DB check error: {e}")
        return 0

def main():
    pipeline_start = time.time()

    # Step 1: Scrape
    if not run_step("Scraping Market News", ["scraper.py"]):
        sys.exit(1)

    # Step 2: Synthesize (Loops until all newly scraped articles are processed)
    pending = get_pending_count()
    print(f"\nArticles awaiting AI synthesis: {pending}")

    while pending > 0:
        print(f"Processing batch ({pending} remaining)...")
        if not run_step("AI Synthesis", ["synthesize.py"]):
            break
        new_pending = get_pending_count()
        if new_pending >= pending:  # Prevent infinite loop if an article keeps failing
            print("No progress made on pending batch; stopping loop.")
            break
        pending = new_pending

    total_time = time.time() - pipeline_start
    print(f"\n✔ Full Pipeline completed in {total_time:.1f}s")

if __name__ == "__main__":
    main()
