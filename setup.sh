#!/bin/bash
set -e

echo "=== 1. Updating System Packages ==="
apt update && apt install -y python3-pip python3-venv git curl sqlite3

echo "=== 2. Installing Ollama & Pulling Qwen2.5:3b ==="
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi
systemctl enable --now ollama
sleep 5
ollama pull qwen2.5:3b

echo "=== 3. Setting up Python Virtual Environment ==="
mkdir -p /opt/explainer-service/data
cd /opt/explainer-service
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "=== 4. Configuring Systemd Services ==="
cp system/explainer-api.service /etc/systemd/system/explainer-api.service
systemctl daemon-reload
systemctl enable --now explainer-api

echo "=== 5. Setting up Cron Job ==="
chmod +x run_pipeline.sh
(crontab -l 2>/dev/null | grep -v "run_pipeline.sh" ; cat system/crontab.txt) | crontab -

echo "=== Setup Complete! API is running on port 8000. ==="
systemctl status explainer-api --no-pager
