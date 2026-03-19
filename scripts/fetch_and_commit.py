#!/usr/bin/env python3
"""
Daily AI News Fetcher
获取最新AI资讯，生成Markdown并提交到GitHub
"""

import os
import subprocess
import requests
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

# 配置
PROJECT_DIR = Path("/root/projects/daily-ai-news")
ARCHIVES_DIR = PROJECT_DIR / "archives"
TODAY_FILE = ARCHIVES_DIR / f"ai-news-{datetime.now().strftime('%Y-%m-%d')}.md"
README_FILE = PROJECT_DIR / "README.md"
LOG_FILE = PROJECT_DIR / "fetch_log.txt"

# 可选：设置 NewsAPI Key（免费获取：https://newsapi.org/）
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

def run_command(cmd, check=True):
    """执行shell命令"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ 命令失败: {cmd}")
        print(f"错误: {result.stderr}")
    return result

def log(message):
    """记录日志"""
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def clean_html(html):
    """清理HTML标签"""
    import html
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', html)
    # 解码HTML实体
    text = html.unescape(text)
    return text.strip()

def fetch_from_rss():
    """从中文和英文RSS源获取AI新闻"""
    news_items = {
        'headlines': [],
        'model_releases': [],
        'funding': [],
        'policy': [],
        'products': []
    }

    # 中文RSS源
    cn_feeds = [
        "https://www.36kr.com/feed/search/keyword/人工智能",
        "https://www.ifanr.com/rss",
    ]

    # 英文RSS源（主要科技媒体）
    en_feeds = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.artificialintelligence-news.com/feed/",
    ]

    all_feeds = cn_feeds + en_feeds

    try:
        import feedparser

        for feed_url in all_feeds:
            try:
                print(f"  📡 获取: {feed_url[:50]}...")
                feed = feedparser.parse(feed_url)

                for entry in feed.entries[:8]:
                    title = entry.get('title', '')
                    description = entry.get('description', entry.get('summary', ''))
                    url = entry.get('link', '')
                    published = entry.get('published', '')

                    # 清理HTML
                    description = clean_html(description)
                    description = description[:200] + '...' if len(description) > 200 else description

                    # 判断来源类型
                    is_cn = any(domain in feed_url for domain in ['36kr', 'ifanr', 'csdn', 'zhihu'])
                    source = entry.get('title', '') if is_cn else 'RSS'

                    # 判断新闻类别
                    title_lower = title.lower()
                    desc_lower = description.lower()

                    item = {
                        'title': title,
                        'url': url,
                        'description': description,
                        'published': published,
                        'source': source
                    }

                    # 模型发布
                    if any(word in title_lower for word in ['gpt', 'claude', 'gemini', 'llama', '模型发布', 'model release', 'openai']):
                        news_items['model_releases'].append(item)
                    # 融资
                    elif any(word in title_lower for word in ['融资', 'funding', '投资', 'investment', 'ipo', 'unicorn']):
                        news_items['funding'].append(item)
                    # 政策监管
                    elif any(word in title_lower for word in ['监管', '政策', 'regulation', 'policy', 'law', '法规']):
                        news_items['policy'].append(item)
                    # 产品发布
                    elif any(word in title_lower for word in ['发布', 'launch', 'release', '推出', '产品', 'product']):
                        news_items['products'].append(item)
                    # 其他头条
                    else:
                        news_items['headlines'].append(item)

            except Exception as e:
                log(f"RSS获取错误 {feed_url}: {str(e)}")

    except ImportError:
        log("feedparser未安装，跳过RSS订阅源")

    return news_items

def fetch_from_github_trending():
    """获取GitHub热门AI项目"""
    try:
        url = "https://api.github.com/search/repositories"
        params = {
            'q': 'artificial intelligence OR machine learning OR LLM OR "deep learning" language:Python',
            'sort': 'stars',
            'order': 'desc',
            'per_page': 8
        }

        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            repos = response.json().get('items', [])
            return [
                {
                    'name': repo['name'],
                    'url': repo['html_url'],
                    'stars': repo['stargazers_count'],
                    'description': repo.get('description', '暂无描述')
                }
                for repo in repos
            ]
    except Exception as e:
        log(f"GitHub热门项目获取错误: {str(e)}")

    return []

def fetch_from_huggingface():
    """获取HuggingFace热门模型"""
    try:
        # HuggingFace API - 获取热门模型
        url = "https://huggingface.co/api/models"
        params = {
            'limit': 6,
            'sort': 'downloads',
            'direction': '-1'
        }

        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            models = response.json()
            return [
                {
                    'id': model.get('modelId', ''),
                    'url': f"https://huggingface.co/{model.get('modelId', '')}",
                    'downloads': model.get('downloads', 0),
                    'likes': model.get('likes', 0),
                    'description': model.get('description', '')[:100]
                }
                for model in models
            ]
    except Exception as e:
        log(f"HuggingFace获取错误: {str(e)}")

    return []

def fetch_ai_news():
    """从多个来源获取AI资讯"""
    print(f"\n{'='*60}")
    print(f"🔍 正在获取AI资讯 - {datetime.now().strftime('%Y年%m月%d日')}")
    print(f"{'='*60}\n")

    all_news = {
        'headlines': [],
        'model_releases': [],
        'funding': [],
        'policy': [],
        'products': [],
        'github_trending': [],
        'huggingface': []
    }

    # 获取RSS新闻
    print("📡 正在获取RSS订阅源...")
    rss_news = fetch_from_rss()
    all_news['headlines'].extend(rss_news['headlines'][:6])
    all_news['model_releases'].extend(rss_news['model_releases'][:5])
    all_news['funding'].extend(rss_news['funding'][:5])
    all_news['policy'].extend(rss_news['policy'][:5])
    all_news['products'].extend(rss_news['products'][:5])

    # 获取GitHub热门项目
    print("📡 正在获取GitHub热门AI项目...")
    all_news['github_trending'] = fetch_from_github_trending()

    # 获取HuggingFace热门模型
    print("📡 正在获取HuggingFace热门模型...")
    all_news['huggingface'] = fetch_from_huggingface()

    # 统计
    print(f"\n✅ 获取头条新闻: {len(all_news['headlines'])} 条")
    print(f"✅ 获取模型发布: {len(all_news['model_releases'])} 条")
    print(f"✅ 获取融资新闻: {len(all_news['funding'])} 条")
    print(f"✅ 获取政策监管: {len(all_news['policy'])} 条")
    print(f"✅ 获取产品发布: {len(all_news['products'])} 条")
    print(f"✅ 获取GitHub热门: {len(all_news['github_trending'])} 个")
    print(f"✅ 获取HuggingFace: {len(all_news['huggingface'])} 个")

    return generate_content(all_news)

def format_news_item(item):
    """格式化新闻条目为Markdown"""
    title = item.get('title', '')
    url = item.get('url', '')
    desc = item.get('description', '')[:150]
    source = item.get('source', '资讯')

    if url:
        return f"- [{title}]({url})\n  > {desc}… — *{source}*"
    else:
        return f"- {title}\n  > {desc}…"

def generate_content(news_data):
    """生成Markdown内容"""
    date_str = datetime.now().strftime('%Y年%m月%d日')
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    content = f"""# 📊 AI 每日资讯汇总 - {date_str}

> 更新时间：{update_time}

---

## 🔥 今日头条

"""

    # 头条新闻
    if news_data['headlines']:
        for item in news_data['headlines'][:8]:
            content += format_news_item(item) + "\n\n"
    else:
        content += "*暂无最新头条*\n\n"

    # 模型发布
    content += "## 🆕 模型发布\n\n"
    if news_data['model_releases']:
        content += "| 来源 | 模型/产品 | 时间 |\n"
        content += "|------|----------|------|\n"
        for item in news_data['model_releases'][:6]:
            title = item.get('title', '-')[:35]
            source = item.get('source', '资讯')[:15]
            content += f"| {source} | [{title}]({item.get('url', '')}) | {datetime.now().strftime('%m-%d')} |\n"
    else:
        content += "*暂无最新模型发布*\n\n"

    # 产品发布
    content += "\n## 📦 产品发布\n\n"
    if news_data['products']:
        for item in news_data['products'][:5]:
            content += format_news_item(item) + "\n\n"
    else:
        content += "*暂无最新产品发布*\n\n"

    # 融资新闻
    content += "\n## 💰 融资与投资\n\n"
    if news_data['funding']:
        for item in news_data['funding'][:5]:
            content += format_news_item(item) + "\n\n"
    else:
        content += "*暂无最新融资新闻*\n\n"

    # 政策监管
    content += "\n## 🏛️ 政策与监管\n\n"
    if news_data['policy']:
        for item in news_data['policy'][:5]:
            content += format_news_item(item) + "\n\n"
    else:
        content += "*暂无最新政策新闻*\n\n"

    # GitHub热门项目
    content += "\n## 🔥 GitHub AI 项目热门\n\n"
    if news_data['github_trending']:
        for repo in news_data['github_trending']:
            content += f"- [{repo['name']}]({repo['url']}) ⭐ {repo['stars']:,}\n  > {repo.get('description', '暂无描述')}\n\n"
    else:
        content += "*暂无热门项目*\n\n"

    # HuggingFace热门模型
    content += "\n## 🤗 HuggingFace 热门模型\n\n"
    if news_data['huggingface']:
        for model in news_data['huggingface']:
            content += f"- [{model['id']}]({model['url']}) 📥 {model['downloads']:,} 下载 | 👍 {model['likes']:,} 点赞\n"
            if model.get('description'):
                content += f"  > {model['description'][:100]}…\n\n"
            else:
                content += "\n"
    else:
        content += "*暂无热门模型*\n\n"

    # 页脚
    content += """---

**数据来源**：TechCrunch、AI-News、GitHub、HuggingFace

*本文件由 [daily-ai-news](https://github.com/chenjingxiong/daily-ai-news) 自动生成*
"""

    return content

def save_markdown(content):
    """保存Markdown文件"""
    ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)
    with open(TODAY_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Markdown已保存：{TODAY_FILE}")
    return TODAY_FILE

def update_readme():
    """更新README文件"""
    # 获取所有归档文件（按日期降序）
    archives = sorted(ARCHIVES_DIR.glob("ai-news-*.md"), reverse=True)

    archive_links = ""
    for archive in archives[:10]:  # 显示最近10天
        archive_date = archive.stem.replace('ai-news-', '')
        try:
            formatted_date = datetime.strptime(archive_date, '%Y-%m-%d').strftime('%m月%d日')
            archive_links += f"- [{formatted_date}](archives/{archive.name})\n"
        except:
            archive_links += f"- [{archive_date}](archives/{archive.name})\n"

    readme_content = f"""# 🤖 AI 每日资讯

> 自动收集最新 AI 行业资讯，每日更新

## 📅 最新资讯

**[{datetime.now().strftime('%Y年%m月%d日')}]({TODAY_FILE.name})**

## 📚 历史存档

{archive_links}

[查看更多存档 →](./archives/)

## ⚙️ 资讯内容

每日自动更新，涵盖：
- 💰 **融资新闻** - AI初创公司投融资动态
- 🆕 **模型发布** - GPT、Claude、Gemini等大模型更新
- 📦 **产品发布** - AI新产品和服务上线
- 🏛️ **政策监管** - AI法规和政策动态
- 🔥 **热门项目** - GitHub AI项目趋势
- 🤗 **热门模型** - HuggingFace模型排行

## 🔧 技术实现

- **语言**：Python 3
- **定时任务**：系统 Crontab（每日7:00）
- **数据来源**：RSS订阅源、GitHub API、HuggingFace API
- **自动部署**：Git 推送到 GitHub

---

*自动生成于 {datetime.now().strftime('%Y年%m月%d日 %H:%M')}*
"""
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"✅ README已更新")

def commit_to_github():
    """提交更改到GitHub"""
    os.chdir(PROJECT_DIR)

    if not (PROJECT_DIR / ".git").exists():
        print("⚠️  Git仓库未初始化")
        return

    # 添加所有更改
    run_command("git add .")
    print("✅ 文件已暂存")

    # 检查是否有更改
    status = run_command("git status --porcelain", check=False)
    if not status.stdout.strip():
        print("ℹ️  没有新的更改")
        return

    # 提交
    date_str = datetime.now().strftime('%Y-%m-%d')
    commit_msg = f"🤖 AI资讯更新 - {date_str}"
    run_command(f'git commit -m "{commit_msg}"')
    print(f"✅ 已提交：{commit_msg}")

    # 推送
    result = run_command("git push")
    if result.returncode == 0:
        print("✅ 已推送到GitHub")
    else:
        print("⚠️  推送失败 - 请检查GitHub认证")

def main():
    """主函数"""
    log("=== 开始获取AI资讯 ===")

    print("\n" + "="*60)
    print("🤖 AI 每日资讯获取器")
    print("="*60)

    try:
        # 获取资讯
        content = fetch_ai_news()

        # 保存Markdown
        save_markdown(content)

        # 更新README
        update_readme()

        # 提交到GitHub
        commit_to_github()

        log("=== AI资讯获取完成 ===")

        print("\n" + "="*60)
        print("✅ 所有任务完成！")
        print("="*60 + "\n")

    except Exception as e:
        error_msg = f"错误：{str(e)}"
        print(f"\n❌ {error_msg}\n")
        log(error_msg)
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
