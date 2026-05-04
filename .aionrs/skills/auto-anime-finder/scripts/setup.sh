#!/bin/bash
# Setup script for AutoAnimeFinder
# Installs backend dependencies and builds the frontend

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$SKILL_DIR/assets/backend"
FRONTEND_DIR="$SKILL_DIR/assets/frontend"

echo "🔧 Setting up AutoAnimeFinder..."

# Backend setup
echo "📦 Installing backend dependencies..."
cd "$BACKEND_DIR"
python3 -m venv venv 2>/dev/null || true
. venv/bin/activate 2>/dev/null || true
pip install -r requirements.txt -q 2>&1 | tail -3

# Frontend setup
echo "📦 Installing frontend dependencies..."
cd "$FRONTEND_DIR"
npm install --silent 2>&1 | tail -3

echo "🏗️  Building frontend..."
npm run build 2>&1 | tail -5

echo ""
echo "✅ Setup complete!"
echo ""
echo "Run: animesoul start"
echo "Then visit: http://localhost:5173"