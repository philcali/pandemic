#!/bin/bash

# Build script for pandemic-console
set -e

echo "🏗️  Building Pandemic Console..."

# Navigate to frontend directory
cd src/frontend

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
fi

# Build React app
echo "⚛️  Building React application..."
npm run build

# Copy build to Python package console directory
echo "📁 Copying build to package console directory..."
mkdir -p ../pandemic_console/console
rm -rf ../pandemic_console/console/*
cp -r build/* ../pandemic_console/console/

# Go back to package root
cd ../..

# Reinstall package to include new console files
echo "📦 Reinstalling package with console files..."
pip install -e .

echo "✅ Build complete!"
echo ""
echo "Console files structure:"
echo "  pandemic_console/console/index.html"
echo "  pandemic_console/console/static/js/..."
echo "  pandemic_console/console/static/css/..."
echo ""
echo "To run the console:"
echo "1. Start: python -m pandemic_console.service"
echo "2. Visit: http://localhost:3000"