#!/bin/bash
# Script to install the latest Python version on macOS

echo "🔍 Checking current Python version..."
python3 --version

echo ""
echo "📦 Installing latest Python via Homebrew..."
echo "Note: You may need to enter your password for sudo commands"

# Fix Homebrew permissions if needed
echo "🔧 Fixing Homebrew permissions..."
sudo chown -R $(whoami) /opt/homebrew/Cellar

# Update Homebrew
echo "🔄 Updating Homebrew..."
brew update

# Install latest Python (3.12 is the latest stable as of 2024)
echo "⬇️  Installing Python 3.12..."
brew install python@3.12

# Link it
echo "🔗 Linking Python..."
brew link --overwrite python@3.12

# Verify installation
echo ""
echo "✅ Installation complete! Verifying..."
python3.12 --version

echo ""
echo "📝 Note: You may need to update your PATH or use 'python3.12' instead of 'python3'"
echo "   To make it default, add to your ~/.zshrc:"
echo "   export PATH=\"/opt/homebrew/opt/python@3.12/bin:\$PATH\""
