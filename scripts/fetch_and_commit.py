#!/usr/bin/env python3
"""
Daily AI News Fetcher
Fetches latest AI news, generates markdown, and commits to GitHub
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_DIR = Path("/root/projects/daily-ai-news")
ARCHIVES_DIR = PROJECT_DIR / "archives"
TODAY_FILE = ARCHIVES_DIR / f"ai-news-{datetime.now().strftime('%Y-%m-%d')}.md"
README_FILE = PROJECT_DIR / "README.md"
REPO_URL = os.getenv("GITHUB_REPO_URL", "")

def run_command(cmd, check=True):
    """Run shell command"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {result.stderr}")
    return result

def fetch_ai_news():
    """
    Fetch AI news from various sources
    In production, integrate with real news APIs
    """
    print(f"\n{'='*60}")
    print(f"🔍 Fetching AI News - {datetime.now().strftime('%Y年%m月%d日')}")
    print(f"{'='*60}\n")

    # TODO: Integrate with actual news APIs
    # For demo, return template content
    return generate_template_content()

def generate_template_content():
    """Generate markdown template for AI news"""
    date_str = datetime.now().strftime('%Y年%m月%d日')
    return f"""# 📊 AI 每日资讯汇总 - {date_str}

> 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 🔥 头条要闻

<!-- TODO: Add actual news content here -->

## 🆕 模型发布

| 公司 | 模型 | 发布时间 |
|------|------|----------|
<!-- TODO: Add model releases -->

## 💰 融资与投资

<!-- TODO: Add funding news -->

## 🏛️ 政策与监管

<!-- TODO: Add policy news -->

## 📈 行业趋势

<!-- TODO: Add industry trends -->

---

**数据来源**: 自动收集整理

*本文件由 [daily-ai-news](https://github.com/yourusername/daily-ai-news) 自动生成*
"""

def save_markdown(content):
    """Save content to markdown file"""
    ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)
    with open(TODAY_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Markdown saved: {TODAY_FILE}")
    return TODAY_FILE

def update_readme():
    """Update README with latest entry"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    readme_content = f"""# 🤖 Daily AI News

> 每日自动收集最新 AI 行业资讯

## 📅 最新资讯

- [{datetime.now().strftime('%Y年%m月%d日')}]({TODAY_FILE.name})

## 📚 历史存档

详见 [archives/](./archives/) 目录

## ⚙️ 说明

本项目由自动化脚本每日更新，收集 AI 行业最新资讯包括：
- 💰 融资新闻
- 🆕 模型发布
- 🏛️ 政策监管
- 📈 行业趋势

---

*自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"✅ README updated")

def commit_to_github():
    """Commit changes to GitHub"""
    os.chdir(PROJECT_DIR)

    # Check if git repo exists
    if not (PROJECT_DIR / ".git").exists():
        print("⚠️  Git repository not initialized yet")
        print("   Please run: cd /root/projects/daily-ai-news && gh repo create daily-ai-news --public --source=. --push")
        return

    # Add all changes
    run_command("git add .")
    print("✅ Files staged")

    # Commit
    date_str = datetime.now().strftime('%Y-%m-%d')
    commit_msg = f"🤖 AI News Update - {date_str}"
    run_command(f'git commit -m "{commit_msg}"')
    print(f"✅ Committed: {commit_msg}")

    # Push
    result = run_command("git push")
    if result.returncode == 0:
        print("✅ Pushed to GitHub")
    else:
        print("⚠️  Push failed - check GitHub authentication")

def main():
    """Main function"""
    print("\n" + "="*60)
    print("🤖 Daily AI News Fetcher")
    print("="*60)

    # Fetch news
    content = fetch_ai_news()

    # Save markdown
    save_markdown(content)

    # Update README
    update_readme()

    # Commit to GitHub
    commit_to_github()

    print("\n" + "="*60)
    print("✅ All tasks completed!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
