import json
import sqlite3
import re
import requests

DB_PATH = "/opt/explainer-service/data/news.db"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "qwen2.5:3b"

SYSTEM_PROMPT = """You are a senior financial journalist and educator writing for an Indian personal finance platform adhering to strict Google AdSense YMYL standards.

Your objective: Convert the provided raw news text into a thorough, factually accurate, structured explainer article (target 500-650 words).

CRITICAL ACCURACY RULES:
1. Stay strictly anchored to the facts, numbers, and policies in the provided text.
2. If the text covers Government DA/DR, Pay Commissions, or Salaries:
   - Discuss Basic Pay, Dearness Allowance percentage revisions, and household cash flow.
   - NEVER claim mutual fund managers adjust portfolio stock weights based on state DA hikes.
3. If the text covers Gold/Bullion:
   - Discuss spot rates, purity (22K/24K), making charges, and GST.
4. If the text covers Fuel/Taxes:
   - Discuss excise duties, VAT, and transport costs.
5. All numerical examples MUST be mathematically accurate and relevant to the actual topic.

STRUCTURE REQUIREMENTS (You MUST use these exact markdown headers):
## Understanding the Policy & Market Context
(Explain the exact notification, figures, percentages, dates, and background from the source)

## Impact on Personal Cash Flow & Budgets
(Explain how household finances, disposable income, or spending power are influenced)

## Step-by-Step Practical Calculation Example
(Provide a complete, realistic mathematical breakdown using Indian rupees [₹] based on the article's numbers)

## Actionable Takeaways for Readers
(Provide 3 to 4 clear, high-utility bullet points)

Output format must be strictly valid JSON matching this schema:
{
  "title": "Compelling educational headline (max 90 chars)",
  "summary": "2 concise sentences capturing the core takeaway",
  "content": "Full markdown content with all 4 section headings and double line spacing"
}
"""

def get_target_article():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Pick pending articles or drafts that fell below the 350-word publish gate
    cur.execute("""
        SELECT id, slug, title, summary, content, primary_calculator
        FROM explainers
        WHERE ai_transformed = 0 OR status = 'draft'
        ORDER BY id DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()
    return row

def generate_via_ollama(title: str, summary: str, body_content: str, calc: str):
    # Pass up to 3500 chars of genuine editorial body text to eliminate hallucinations
    context_text = body_content.strip() if body_content and len(body_content.strip()) > 200 else summary

    user_prompt = f"""HEADLINE: {title}
RELEVANT TOOL: {calc or 'Financial Planning Calculator'}

RAW SOURCE MATERIAL:
\"\"\"
{context_text[:3500]}
\"\"\"

Write the comprehensive, factually accurate 500-650 word explainer covering all 4 sections. Ensure all numbers reflect the source text."""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_ctx": 4096,
            "num_predict": 1400
        }
    }

    res = requests.post(OLLAMA_URL, json=payload, timeout=180)
    if res.status_code == 200:
        data = res.json()
        raw_output = data["message"]["content"]
        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            print("[WARN] JSON decode failed, attempting regex cleanup...")
            match = re.search(r'\{.*\}', raw_output, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return None
    else:
        print(f"Ollama error: {res.status_code} - {res.text}")
        return None

def update_explainer(explainer_id: int, transformed: dict):
    raw_content = transformed.get("content", "")

    # Normalize newlines
    content = raw_content.replace("\\n", "\n")
    
    # Ensure headings always have double line breaks before them
    content = re.sub(r'([^\n])\s*(##+ )', r'\1\n\n\2', content)
    
    # Ensure bullet points start on a new line
    content = re.sub(r'([^\n])\s*(- )', r'\1\n\n\2', content)

    words = len(re.findall(r'\w+', content))
    status = "ready" if words >= 350 else "draft"

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE explainers 
        SET title = ?, summary = ?, content = ?, ai_transformed = 1, word_count = ?, status = ?
        WHERE id = ?
    """, (
        transformed["title"],
        transformed["summary"],
        content,
        words,
        status,
        explainer_id
    ))
    conn.commit()
    conn.close()
    return words, status

def run():
    item = get_target_article()
    if not item:
        print("No articles need transformation.")
        return

    print(f"\nSynthesizing ID {item['id']}: {item['title'][:60]}...")
    try:
        result = generate_via_ollama(
            title=item["title"],
            summary=item["summary"],
            body_content=item["content"],
            calc=item["primary_calculator"]
        )
        if result and "content" in result and "title" in result:
            words, status = update_explainer(item["id"], result)
            print(f"[RESULT] Finished ID {item['id']}! Words: {words} | Status: {status}")
            print(f"Title: {result['title']}")
        else:
            print(f"[ERROR] Invalid output from model.")
    except Exception as e:
        print(f"[ERROR] Exception: {e}")

if __name__ == "__main__":
    run()
