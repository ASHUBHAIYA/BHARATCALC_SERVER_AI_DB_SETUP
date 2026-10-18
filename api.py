import json
import sqlite3
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

app = FastAPI(title="Explainers API & Admin Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/opt/explainer-service/data/news.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------- WEB BROWSER TABLE VIEW -----------------
@app.get("/dashboard", response_class=HTMLResponse)
def render_dashboard(status: str = Query(None)):
    conn = get_db()
    cur = conn.cursor()
    
    query = """
        SELECT id, slug, title, summary, category, primary_calculator,
               ai_transformed, word_count, status, created_at
        FROM explainers
    """
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
        
    query += " ORDER BY id DESC"
    cur.execute(query, tuple(params))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    # Generate table rows
    table_rows_html = ""
    for item in rows:
        badge_color = "#16a34a" if item["status"] == "ready" else "#d97706"
        ai_badge = '<span style="color:#16a34a; font-weight:600;">✓ Transformed</span>' if item["ai_transformed"] else '<span style="color:#dc2626;">✗ Raw Scraped</span>'
        calc = item["primary_calculator"] or '<span style="color:#94a3b8;">None</span>'
        
        table_rows_html += f"""
        <tr>
            <td style="font-weight:600; color:#334155;">#{item["id"]}</td>
            <td style="max-width:320px;">
                <div style="font-weight:600; color:#0f172a; margin-bottom:4px;">{item["title"]}</div>
                <div style="font-size:12px; color:#64748b; line-height:1.4;">{item["summary"][:140]}...</div>
            </td>
            <td><span class="badge" style="background:#e0f2fe; color:#0369a1;">{item["category"]}</span></td>
            <td><code>{calc}</code></td>
            <td style="text-align:center;">{ai_badge}</td>
            <td style="text-align:center; font-weight:600;">{item["word_count"]}</td>
            <td style="text-align:center;">
                <span class="badge" style="background:{badge_color}22; color:{badge_color}; border:1px solid {badge_color}55;">
                    {item["status"].upper()}
                </span>
            </td>
            <td style="white-space:nowrap; font-size:12px; color:#64748b;">{item["created_at"][:16]}</td>
            <td style="text-align:center;">
                <a href="/api/explainers/{item['slug']}" target="_blank" class="btn">View JSON</a>
            </td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Explainers Database Dashboard</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: #f8fafc;
                margin: 0;
                padding: 24px;
                color: #0f172a;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}
            .title {{
                font-size: 24px;
                font-weight: 700;
            }}
            .filters {{
                display: flex;
                gap: 10px;
                align-items: center;
            }}
            .filter-link {{
                padding: 6px 12px;
                border-radius: 6px;
                text-decoration: none;
                font-size: 13px;
                font-weight: 500;
                color: #475569;
                background: #e2e8f0;
            }}
            .filter-link.active {{
                background: #2563eb;
                color: #ffffff;
            }}
            .card {{
                background: #ffffff;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                overflow-x: auto;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                text-align: left;
                font-size: 14px;
            }}
            th {{
                background-color: #f1f5f9;
                padding: 12px 14px;
                font-weight: 600;
                color: #475569;
                border-bottom: 1px solid #cbd5e1;
            }}
            td {{
                padding: 12px 14px;
                border-bottom: 1px solid #f1f5f9;
                vertical-align: middle;
            }}
            tr:hover {{
                background-color: #f8fafc;
            }}
            .badge {{
                display: inline-block;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 700;
                border-radius: 9999px;
            }}
            code {{
                background: #f1f5f9;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 12px;
                color: #0f172a;
            }}
            .btn {{
                text-decoration: none;
                padding: 4px 8px;
                background: #0284c7;
                color: white;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
            }}
            .btn:hover {{
                background: #0369a1;
            }}
            #searchInput {{
                padding: 7px 12px;
                border-radius: 6px;
                border: 1px solid #cbd5e1;
                font-size: 13px;
                width: 220px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <div class="title">Explainers Management Dashboard</div>
                <div style="font-size:13px; color:#64748b; margin-top:4px;">Total records loaded: <b>{len(rows)}</b></div>
            </div>
            <div class="filters">
                <input type="text" id="searchInput" placeholder="Quick search..." onkeyup="filterTable()">
                <a href="/dashboard" class="filter-link {'active' if not status else ''}">All</a>
                <a href="/dashboard?status=ready" class="filter-link {'active' if status == 'ready' else ''}">Ready</a>
                <a href="/dashboard?status=draft" class="filter-link {'active' if status == 'draft' else ''}">Drafts</a>
            </div>
        </div>

        <div class="card">
            <table id="explainersTable">
                <thead>
                    <tr>
                        <th style="width: 50px;">ID</th>
                        <th>Title & Summary</th>
                        <th>Category</th>
                        <th>Attached Tool</th>
                        <th style="text-align:center;">AI Transformed</th>
                        <th style="text-align:center;">Words</th>
                        <th style="text-align:center;">Status</th>
                        <th>Created</th>
                        <th style="text-align:center;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
        </div>

        <script>
            function filterTable() {{
                const input = document.getElementById("searchInput").value.toLowerCase();
                const rows = document.querySelectorAll("#explainersTable tbody tr");
                rows.forEach(row => {{
                    const text = row.innerText.toLowerCase();
                    row.style.display = text.includes(input) ? "" : "none";
                }});
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# ----------------- JSON API ENDPOINTS -----------------
@app.get("/api/explainers")
def list_explainers(limit: int = 20, offset: int = 0, category: str = Query(None)):
    conn = get_db()
    cur = conn.cursor()

    base_query = """
        SELECT id, slug, title, summary, category, primary_calculator,
               related_calculators, word_count, source_reference, published_at, created_at
        FROM explainers
        WHERE ai_transformed = 1 AND status = 'ready'
    """
    params = []

    if category:
        base_query += " AND category = ?"
        params.append(category)

    base_query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cur.execute(base_query, tuple(params))
    rows = cur.fetchall()
    conn.close()

    items = []
    for row in rows:
        item = dict(row)
        item["related_calculators"] = json.loads(item["related_calculators"] or "[]")
        items.append(item)

    return {"explainers": items, "count": len(items)}

@app.get("/api/explainers/{slug}")
def get_explainer(slug: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM explainers WHERE slug = ?", (slug,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Explainer not found")

    item = dict(row)
    item["related_calculators"] = json.loads(item["related_calculators"] or "[]")
    return item
