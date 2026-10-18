#!/bin/bash
set -e
cd /opt/explainer-service

# 1. Scrape latest financial articles
/opt/explainer-service/venv/bin/python scraper.py >> /var/log/explainer_pipeline.log 2>&1

# 2. Synthesize pending explainers with Ollama
while /opt/explainer-service/venv/bin/python synthesize.py | grep -q "Finished ID"; do
    sleep 5
done >> /var/log/explainer_pipeline.log 2>&1
