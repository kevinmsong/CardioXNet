#!/bin/bash
set -e

echo "🚀 Deploying CardioXNet to GitHub Pages..."

# Navigate to frontend
cd frontend

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Install gh-pages if not already installed
npm install --save-dev gh-pages

# Add deploy script if not exists
npm pkg set scripts.deploy="gh-pages -d dist"

# Build production bundle
echo "🔨 Building production bundle..."
npm run build

# Deploy to GitHub Pages
echo "🌐 Deploying to GitHub Pages..."
npm run deploy

echo "✅ Deployment complete!"
echo "🌍 Your site will be available at: https://kevinmsong.github.io/CardioXNet/"
echo "⏱️  It may take 1-2 minutes for changes to appear"
