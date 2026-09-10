#!/bin/bash
set -euo pipefail
cd /opt/mirage/mirage-mcp
git fetch origin master
git reset --hard origin/master
docker compose up --build -d
docker compose ps
