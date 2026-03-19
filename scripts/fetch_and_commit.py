#!/usr/bin/env python3
"""
Daily AI News Fetcher
Fetches latest AI news, generates markdown, and commits to GitHub
"""

import os
import subprocess
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
PROJECT_DIR = Path("/root/projects/daily-ai-news")
ARCHIVES_DIR = PROJECT_DIR / "archives"
TODAY_FILE = ARCHIVES_DIR / f"ai-news-{datetime.now().strftime('%Y-%m-%d')}.md"
README_FILE = PROJECT_DIR / "README.md"
LOG_FILE = PROJECT_DIR / "fetch_log.txt"

# Optional: Set your NewsAPI key here for better results
# Get free key at: https://newsapi.org/
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

def run_command(cmd, check=True):
    """Run shell command"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {result.stderr}")
    return result

def log(message):
    """Log message to file"""
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def fetch_from_newsapi():
    """Fetch news from NewsAPI (requires API key)"""
    if not NEWS_API_KEY:
        return None

    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')

        url = "https://newsapi.org/v2/everything"
        params = {
            'q': 'artificial intelligence OR AI OR machine learning OR "large language model" OR GPT OR ChatGPT',
            'from': yesterday,
            'to': today,
            'language': 'en',
            'sortBy': 'publishedAt',
            'apiKey': NEWS_API_KEY,
            'pageSize': 20
        }

        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json().get('articles', [])
        else:
            log(f"NewsAPI error: {response.status_code}")
            return None
    except Exception as e:
        log(f"NewsAPI exception: {str(e)}")
        return None

def fetch_from_technews():
    """Fetch AI news from tech news RSS feeds"""
    news_items = []

    # RSS feeds to check
    rss_feeds = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.artificialintelligence-news.com/feed/",
    ]

    try:
        import feedparser

        for feed_url in rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:  # Get 5 latest from each feed
                    news_items.append({
                        'title': entry.get('title', ''),
                        'url': entry.get('link', ''),
                        'description': entry.get('description', '')[:200],
                        'published': entry.get('published', ''),
                        'source': feed_url
                    })
            except Exception as e:
                log(f"RSS feed error for {feed_url}: {str(e)}")
    except ImportError:
        log("feedparser not installed, skipping RSS feeds")

    return news_items

def fetch_from_github_trending():
    """Fetch trending AI repositories from GitHub"""
    try:
        url = "https://api.github.com/search/repositories"
        params = {
            'q': 'artificial intelligence OR machine learning OR LLM language:Python',
            'sort': 'stars',
            'order': 'desc',
            'per_page': 5
        }

        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            repos = response.json().get('items', [])
            return [
                {
                    'name': repo['name'],
                    'url': repo['html_url'],
                    'stars': repo['stargazers_count'],
                    'description': repo.get('description', '')
                }
                for repo in repos
            ]
    except Exception as e:
        log(f"GitHub trending error: {str(e)}")

    return []

def fetch_ai_news():
    """
    Fetch AI news from various sources
    """
    print(f"\n{'='*60}")
    print(f"🔍 Fetching AI News - {datetime.now().strftime('%Y年%m月%d日')}")
    print(f"{'='*60}\n")

    all_news = {
        'headlines': [],
        'model_releases': [],
        'funding': [],
        'policy': [],
        'trends': [],
        'github_trending': []
    }

    # Try NewsAPI first (most reliable if key is provided)
    if NEWS_API_KEY:
        print("📡 Fetching from NewsAPI...")
        articles = fetch_from_newsapi()
        if articles:
            for article in articles[:10]:
                title = article.get('title', '').lower()
                all_news['headlines'].append({
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'description': article.get('description', '')[:150],
                    'source': article.get('source', {}).get('name', 'Unknown')
                })

            # Categorize articles
            for article in articles:
                title = article.get('title', '').lower()
                desc = article.get('description', '').lower()

                if any(word in title or word in desc for word in ['gpt', 'claude', 'gemini', 'llama', 'model', 'release']):
                    all_news['model_releases'].append(article)
                elif any(word in title or word in desc for word in ['funding', 'investment', 'raise', 'ipo', 'acquired']):
                    all_news['funding'].append(article)
                elif any(word in title or word in desc for word in ['regulation', 'policy', 'law', 'government', 'eu ai act']):
                    all_news['policy'].append(article)

    # Try RSS feeds
    print("📡 Fetching from RSS feeds...")
    rss_items = fetch_from_technews()
    if rss_items:
        for item in rss_items[:5]:
            all_news['headlines'].append({
                'title': item['title'],
                'url': item['url'],
                'description': item['description'],
                'source': 'RSS'
            })

    # Fetch GitHub trending
    print("📡 Fetching GitHub trending AI repos...")
    all_news['github_trending'] = fetch_from_github_trending()

    print(f"✅ Fetched {len(all_news['headlines'])} headlines")
    print(f"✅ Fetched {len(all_news['model_releases'])} model releases")
    print(f"✅ Fetched {len(all_news['funding'])} funding news")
    print(f"✅ Fetched {len(all_news['policy'])} policy news")
    print(f"✅ Fetched {len(all_news['github_trending'])} trending repos")

    return generate_content(all_news)

def format_news_item(item):
    """Format a news item as markdown"""
    title = item.get('title', item.get('description', ''))[:100]
    url = item.get('url', '')
    desc = item.get('description', '')[:200]
    source = item.get('source', 'Unknown')

    if url:
        return f"- [{title}]({url})\n  > {desc}... — *{source}*"
    else:
        return f"- {title}\n  > {desc}..."

def generate_content(news_data):
    """Generate markdown content from fetched news"""
    date_str = datetime.now().strftime('%Y年%m月%d日')
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    content = f"""# 📊 AI 每日资讯汇总 - {date_str}

> 更新时间: {update_time}

---

## 🔥 头条要闻

"""

    # Add headlines
    if news_data['headlines']:
        for item in news_data['headlines'][:8]:
            content += format_news_item(item) + "\n\n"
    else:
        content += "*暂无最新头条*\n\n"

    # Model releases
    content += """## 🆕 模型发布

| 公司 | 模型 | 发布时间 |
|------|------|----------|
"""

    if news_data['model_releases']:
        for item in news_data['model_releases'][:5]:
            title = item.get('title', 'N/A')[:40]
            source = item.get('source', {}).get('name', 'Unknown') if isinstance(item.get('source'), dict) else 'Unknown'
            content += f"| {source} | [{title}]({item.get('url', '')}) | {datetime.now().strftime('%Y-%m-%d')} |\n"
    else:
        content += "| - | 暂无最新模型发布 | - |\n"

    # Funding news
    content += "\n## 💰 融资与投资\n\n"
    if news_data['funding']:
        for item in news_data['funding'][:5]:
            content += format_news_item(item) + "\n\n"
    else:
        content += "*暂无最新融资新闻*\n\n"

    # Policy news
    content += "\n## 🏛️ 政策与监管\n\n"
    if news_data['policy']:
        for item in news_data['policy'][:5]:
            content += format_news_item(item) + "\n\n"
    else:
        content += "*暂无最新政策新闻*\n\n"

    # GitHub trending
    content += "\n## 🔥 GitHub AI 项目热门\n\n"
    if news_data['github_trending']:
        for repo in news_data['github_trending']:
            content += f"- [{repo['name']}]({repo['url']}) ⭐ {repo['stars']:,}\n  > {repo.get('description', 'No description')}\n\n"
    else:
        content += "*暂无热门项目*\n\n"

    # Footer
    content += """---

**数据来源**: NewsAPI, TechCrunch, AI News, GitHub

*本文件由 [daily-ai-news](https://github.com/chenjingxiong/daily-ai-news) 自动生成*
"""

    return content

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

    # Get all archive files sorted by date (newest first)
    archives = sorted(ARCHIVES_DIR.glob("ai-news-*.md"), reverse=True)

    archive_links = ""
    for archive in archives[:7]:  # Show last 7 days
        archive_date = archive.stem.replace('ai-news-', '')
        try:
            formatted_date = datetime.strptime(archive_date, '%Y-%m-%d').strftime('%Y年%m月%d日')
            archive_links += f"- [{formatted_date}](archives/{archive.name})\n"
        except:
            archive_links += f"- [{archive_date}](archives/{archive.name})\n"

    readme_content = f"""# 🤖 Daily AI News

> 每日自动收集最新 AI 行业资讯

## 📅 最新资讯

- [{datetime.now().strftime('%Y年%m月%d日')}]({TODAY_FILE.name})

## 📚 历史存档

{archive_links}

[查看更多...](./archives/)

## ⚙️ 说明

本项目由自动化脚本每日更新，收集 AI 行业最新资讯包括：
- 💰 融资新闻
- 🆕 模型发布
- 🏛️ 政策监管
- 📈 行业趋势

## 🔧 技术栈

- Python 3
- GitHub Actions (Cron)
- NewsAPI / RSS Feeds
- GitHub API

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
        return

    # Add all changes
    run_command("git add .")
    print("✅ Files staged")

    # Check if there are changes to commit
    status = run_command("git status --porcelain", check=False)
    if not status.stdout.strip():
        print("ℹ️  No changes to commit")
        return

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
    log("=== Starting AI News Fetch ===")

    print("\n" + "="*60)
    print("🤖 Daily AI News Fetcher")
    print("="*60)

    try:
        # Fetch news
        content = fetch_ai_news()

        # Save markdown
        save_markdown(content)

        # Update README
        update_readme()

        # Commit to GitHub
        commit_to_github()

        log("=== AI News Fetch completed successfully ===")

        print("\n" + "="*60)
        print("✅ All tasks completed!")
        print("="*60 + "\n")

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"\n❌ {error_msg}\n")
        log(error_msg)
        raise

if __name__ == "__main__":
    main()
