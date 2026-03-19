#!/bin/bash
# Setup script for Daily AI News GitHub repository

set -e

PROJECT_DIR="/root/projects/daily-ai-news"
cd "$PROJECT_DIR"

echo "=========================================="
echo "🤖 Daily AI News - Setup Script"
echo "=========================================="
echo ""

# Check GitHub authentication
echo "📋 Step 1: Checking GitHub authentication..."
if gh auth status &>/dev/null; then
    echo "✅ GitHub authenticated"
    gh auth status
else
    echo "❌ Not authenticated with GitHub"
    echo "Please run: gh auth login"
    exit 1
fi

echo ""
echo "📋 Step 2: Getting GitHub user info..."
GITHUB_USER=$(gh api user --jq '.login')
echo "✅ GitHub user: @$GITHUB_USER"

echo ""
echo "📋 Step 3: Initializing Git repository..."
if [ ! -d ".git" ]; then
    git init
    git config user.name "Daily AI News Bot"
    git config user.email "news-bot@github.local"
    echo "✅ Git repository initialized"
else
    echo "✅ Git repository already exists"
fi

echo ""
echo "📋 Step 4: Creating initial files..."
# Create .gitignore
cat > .gitignore << 'EOF'
*.pyc
__pycache__/
*.log
.DS_Store
EOF

# Create initial README
cat > README.md << 'EOF'
# 🤖 Daily AI News

> 每日自动收集最新 AI 行业资讯

## 📅 最新资讯

*自动化初始化中...*

## 📚 历史存档

详见 [archives/](./archives/) 目录

## ⚙️ 说明

本项目由自动化脚本每日更新，收集 AI 行业最新资讯。

---

*自动生成*
EOF

echo "✅ Initial files created"

echo ""
echo "📋 Step 5: Creating GitHub repository..."
REPO_NAME="daily-ai-news"

if gh repo view "$GITHUB_USER/$REPO_NAME" &>/dev/null; then
    echo "✅ Repository already exists: https://github.com/$GITHUB_USER/$REPO_NAME"
    git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git" 2>/dev/null || true
else
    echo "📦 Creating repository: $REPO_NAME"
    gh repo create "$REPO_NAME" --public --source=. --push --description="Daily AI News - 自动收集AI行业资讯"
    echo "✅ Repository created: https://github.com/$GITHUB_USER/$REPO_NAME"
fi

echo ""
echo "📋 Step 6: Setting up executable permissions..."
chmod +x scripts/*.py
echo "✅ Permissions set"

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "📍 Repository: https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""
echo "📋 Next steps:"
echo "   1. Configure news sources in scripts/fetch_and_commit.py"
echo "   2. Test manually: python3 scripts/fetch_and_commit.py"
echo "   3. Update crontab to use the new script"
echo ""
echo "   To update crontab:"
echo "   crontab -e"
echo "   # Change the line to:"
echo "   0 7 * * * cd /root/projects/daily-ai-news && python3 scripts/fetch_and_commit.py"
echo ""
