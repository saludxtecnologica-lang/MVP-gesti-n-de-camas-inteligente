#!/bin/bash
set -e

# Script de build para Vercel
echo "📦 Installing dependencies in frontend..."
npm install --prefix frontend

echo "🏗️  Building frontend..."
npm run build --prefix frontend

echo "✅ Build completed successfully!"
