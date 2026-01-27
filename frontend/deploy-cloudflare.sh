#!/bin/bash
set -e

# =============================================================================
# Strava Analyzer Frontend - Cloudflare Pages Deployment
# =============================================================================
# Prerequisites:
#   1. npm install -g wrangler
#   2. wrangler login
# =============================================================================

PROJECT_NAME="strava-dashboard"

echo "Deploying to Cloudflare Pages..."

# Deploy using wrangler
npx wrangler pages deploy . --project-name="${PROJECT_NAME}"

echo ""
echo "=============================================="
echo "Deployment complete!"
echo "=============================================="
echo ""
echo "Your site is available at:"
echo "  https://${PROJECT_NAME}.pages.dev"
echo ""
echo "To use a custom domain (e.g., strava.bngrd.com):"
echo "1. Go to Cloudflare Dashboard > Pages > ${PROJECT_NAME}"
echo "2. Click 'Custom domains' > 'Set up a custom domain'"
echo "3. Enter your domain and follow the DNS instructions"
echo ""
