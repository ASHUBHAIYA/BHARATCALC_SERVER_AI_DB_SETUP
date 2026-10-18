# BharatCalc Financial Explainer & News Intelligence Engine

An automated, self-hosted financial news pipeline and API service built for **BharatCalc**. The engine ingests macroeconomic, market, and personal finance developments from major Indian financial portals, synthesizes them into Google AdSense/YMYL-compliant guides using local LLMs, and serves them to the frontend along with interactive financial calculators.

---

## 1. System Architecture & Tech Stack

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Operating System** | Ubuntu 22.04 / 24.04 LTS | Hosted on Linux VPS (`/opt/explainer-service`) |
| **Web API Engine** | FastAPI + Uvicorn | High-performance async REST API on `0.0.0.0:8000` |
| **Local LLM Engine** | Ollama (`qwen2.5:3b`) | Native local inference, zero API token costs |
| **Article Extraction**| Trafilatura + BeautifulSoup4 | Strips ads, navigation, and paywalls; character-gated |
| **Feed Ingestion** | Feedparser | RSS feeds from Moneycontrol, Economic Times, Livemint |
| **Database** | SQLite3 with WAL Mode | Concurrent reads/writes with specialized index lookups |
| **Public Gateway** | Cloudflare Tunnel (`cloudflared`) | Encrypted SSL tunnel exposing `https://api.authorizetech.in` |
| **Task Automation** | Linux Cron + `flock` | 15-minute pipeline runs with lock-file overlap prevention |

---

## 2. Directory Structure

```text
/opt/explainer-service/
├── api.py                    # FastAPI application, CORS rules, and endpoints
├── scraper.py                # RSS parser, body extraction (trafilatura), calculator rules
├── synthesize.py             # Ollama orchestrator, YMYL editorial prompt, DB updater
├── init_db.py                # Schema migration, WAL mode enable, performance indexes
├── run_pipeline.sh           # Main cron bash wrapper running scraper & synthesis
├── setup.sh                  # One-click bootstrap script for fresh server deployments
├── requirements.txt          # Python virtual environment dependencies
├── README.md                 # System documentation and operational runbook
├── data/
│   ├── news.db               # SQLite database
│   └── backups/              # Automated daily DB snapshots
└── system/
    ├── explainer-api.service # Systemd unit configuration
    ├── crontab.txt           # Cron schedule definition
    ├── logrotate.conf        # Log rotation configuration
    └── cloudflare-config.yml # Cloudflare tunnel configuration reference
3. Local AI Specifications & Constraints
Engine: Ollama

Model: qwen2.5:3b

Context Window (num_ctx): 4096 tokens

Predict Window (num_predict): 1400 tokens

Temperature: 0.3 (Low randomness for financial accuracy)

Target Word Count: 500 – 650 words

Minimum Word Gate: 350 words (ready status threshold; drafts under 350 are withheld from public endpoints)

Editorial & YMYL Guidelines Enforced in Prompt:
Zero Hallucination Policy: Does not mix corporate CTC allowances with Central/State Government Pay Commissions (Basic + DA + HRA).

Contextual Calculator Pairing: Matches topics to specific financial tools (e.g., DA notifications map to inflation-calculator, equity fund rebalancing to sip-investment).

Mandatory 4-Section Markdown Structure:

## Understanding the Policy & Market Context

## Impact on Personal Cash Flow & Budgets

## Step-by-Step Practical Calculation Example

## Actionable Takeaways for Readers

4. Quick Server Setup from Scratch
To rebuild this exact service on a clean Ubuntu VPS:

Bash
# 1. Clone repository
git clone [https://github.com/](https://github.com/)<YOUR_GITHUB_USERNAME>/bharatcalc-explainer-service.git /opt/explainer-service
cd /opt/explainer-service

# 2. Run the automated bootstrap script
sudo bash setup.sh
5. Cloudflare Tunnel Setup (api.authorizetech.in)
To route public HTTPS traffic to the FastAPI service running on port 8000:

Initial Setup on Fresh Server:
Bash
# 1. Install cloudflared
curl -L --output cloudflared.deb [https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb](https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb)
sudo dpkg -i cloudflared.deb

# 2. Login to Cloudflare account
cloudflared tunnel login

# 3. Create named tunnel
cloudflared tunnel create explainer-api

# 4. Route DNS subdomain
cloudflared tunnel route dns explainer-api api.authorizetech.in
Tunnel Configuration (~/.cloudflared/config.yml):
YAML
tunnel: <TUNNEL_UUID>
credentials-file: /root/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: api.authorizetech.in
    service: http://localhost:8000
  - service: http_status:404
Run Tunnel as System Service:
Bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
6. Daily Operations & Useful Commands
Check Live API & Services
Bash
# Check FastAPI service status
sudo systemctl status explainer-api

# Check Ollama status
sudo systemctl status ollama

# Restart API
sudo systemctl restart explainer-api
Run Pipeline Manually
Bash
# Run complete pipeline
bash /opt/explainer-service/run_pipeline.sh

# Run only scraper
/opt/explainer-service/venv/bin/python /opt/explainer-service/scraper.py

# Run only synthesis
/opt/explainer-service/venv/bin/python /opt/explainer-service/synthesize.py
Monitor Cron & Logs
Bash
# Tail live pipeline execution log
tail -f /var/log/explainer_pipeline.log

# Check recent cron triggers
sudo journalctl -u cron -n 20 --no-pager
Inspect Database Directly
Bash
# Inspect latest 5 articles
sqlite3 -header -column /opt/explainer-service/data/news.db "
SELECT id, SUBSTR(title, 1, 40) AS title, primary_calculator, word_count, status, published_at 
FROM explainers ORDER BY id DESC LIMIT 5;
"

# Check article counts by status
sqlite3 /opt/explainer-service/data/news.db "
SELECT status, count(*) FROM explainers GROUP BY status;
"

# Take manual SQLite backup
sqlite3 /opt/explainer-service/data/news.db ".backup '/opt/explainer-service/data/backups/news_backup_$(date +%F).db'"
7. Public Endpoints Reference
Explainers List: GET https://api.authorizetech.in/api/explainers?limit=10&category=personal-finance

Single Explainer by Slug: GET https://api.authorizetech.in/api/explainers/{slug}

Interactive Web Dashboard: GET https://api.authorizetech.in/dashboard

Interactive Swagger UI: GET https://api.authorizetech.in/docs
