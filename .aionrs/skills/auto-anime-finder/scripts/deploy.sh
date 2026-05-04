#!/bin/bash
# Deploy to Render.com
# Prerequisites: render-cli or manual setup at dashboard.render.com

echo "📦 Deploying AutoAnimeFinder to Render..."
echo ""
echo "To deploy manually:"
echo "  1. Push the skill's assets/backend to a Git repo"
echo "  2. In Render dashboard:"
echo "     - Web Service: FastAPI backend (docker run -p 8000:8000 -e PORT=8000 ...)"
echo "     - Static Site: Frontend dist/ folder"
echo "  3. Or use render.yaml blueprint (see references/render-deploy.md)"
echo ""
echo "Or run locally: auto-anime-finder start"