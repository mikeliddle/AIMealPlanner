#!/bin/bash
# Pre-Public Release Verification Script
# Run this script to verify no sensitive files will be exposed when making repository public

echo "🔍 Pre-Public Release Security Check"
echo "===================================="
echo ""

ISSUES_FOUND=0

# Check for .env files
echo "Checking for .env files..."
if find . -name ".env" -not -path "./.git/*" -not -name ".env.example" | grep -q .; then
    echo "❌ ERROR: Found .env file(s)!"
    find . -name ".env" -not -path "./.git/*" -not -name ".env.example"
    ISSUES_FOUND=$((ISSUES_FOUND+1))
else
    echo "✅ No .env files found"
fi
echo ""

# Check for credentials.json
echo "Checking for credentials.json files..."
if find . -name "credentials.json" -not -path "./.git/*" -not -name "*.example" | grep -q .; then
    echo "❌ ERROR: Found credentials.json file(s)!"
    find . -name "credentials.json" -not -path "./.git/*" -not -name "*.example"
    ISSUES_FOUND=$((ISSUES_FOUND+1))
else
    echo "✅ No credentials.json files found"
fi
echo ""

# Check for token.json
echo "Checking for token.json files..."
if find . -name "token.json" -not -path "./.git/*" | grep -q .; then
    echo "❌ ERROR: Found token.json file(s)!"
    find . -name "token.json" -not -path "./.git/*"
    ISSUES_FOUND=$((ISSUES_FOUND+1))
else
    echo "✅ No token.json files found"
fi
echo ""

# Check for data directory files
echo "Checking data directory..."
if [ -d "data" ]; then
    if [ -f "data/credentials.json" ] || [ -f "data/token.json" ]; then
        echo "❌ WARNING: Found sensitive files in data/ directory"
        ls -la data/credentials.json data/token.json 2>/dev/null
        echo "   (These should be in .gitignore and not committed)"
        ISSUES_FOUND=$((ISSUES_FOUND+1))
    else
        echo "✅ No sensitive files in data/ directory"
    fi
else
    echo "ℹ️  data/ directory does not exist (this is fine)"
fi
echo ""

# Check git status for tracked sensitive files
echo "Checking git for tracked sensitive files..."
TRACKED_SENSITIVE=$(git ls-files | grep -E "(\.env$|credentials\.json$|token\.json$)" | grep -v "\.example")
if [ -n "$TRACKED_SENSITIVE" ]; then
    echo "❌ ERROR: Git is tracking sensitive files!"
    echo "$TRACKED_SENSITIVE"
    ISSUES_FOUND=$((ISSUES_FOUND+1))
else
    echo "✅ No sensitive files tracked by git"
fi
echo ""

# Final verdict
echo "===================================="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED!"
    echo ""
    echo "Your repository is ready to be made public."
    echo "No sensitive files detected."
    exit 0
else
    echo "❌ ISSUES FOUND: $ISSUES_FOUND"
    echo ""
    echo "Please remove or add sensitive files to .gitignore before making public."
    echo ""
    echo "To remove a file from git tracking:"
    echo "  git rm --cached <filename>"
    echo ""
    echo "Then commit and push the change."
    exit 1
fi
