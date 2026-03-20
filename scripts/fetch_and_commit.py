#!/usr/bin/env python3
"""
Daily AI News Fetcher
获取最新AI资讯，生成Markdown并提交到GitHub

数据源：
- 中文媒体：36氪、虎嗅、机器之心、量子位
- 英文媒体：TechCrunch、VentureBeat、The Verge
- 开发平台：GitHub、HuggingFace、Papers with Code
"""

import os
import subprocess
import requests
import json
import re
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup
from feedparser import parse
from deep_translator import GoogleTranslator

# ==================== 配置 ====================
PROJECT_DIR = Path("/root/projects/daily-ai-news")
ARCHIVES_DIR = PROJECT_DIR / "archives"
TODAY_FILE = ARCHIVES_DIR / f"ai-news-{datetime.now().strftime('%Y-%m-%d')}.md"
README_FILE = PROJECT_DIR / "README.md"
LOG_FILE = PROJECT_DIR / "fetch_log.txt"

# NewsAPI Key（可选）
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# 翻译缓存
TRANSLATION_CACHE = {}

# ==================== 工具函数 ====================
def run_command(cmd, check=True):
    """执行shell命令"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ 命令失败: {cmd}")
    return result

def log(message):
    """记录日志"""
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def translate_to_chinese(text):
    """将英文翻译成中文（带缓存）"""
    if not text or not text.strip():
        return text

    # 检查是否主要是中文
    chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
    if chinese_chars > len(text) * 0.3:
        return text

    # 检查缓存
    if text in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[text]

    try:
        # 分段翻译
        max_length = 4000
        if len(text) <= max_length:
            translated = GoogleTranslator(source='auto', target='zh-CN').translate(text)
        else:
            translated = ""
            segments = []
            current = ""
            sentences = re.split(r'([.!?。！？\n])', text)
            for i in range(0, len(sentences), 2):
                if i + 1 < len(sentences):
                    segment = sentences[i] + sentences[i + 1]
                else:
                    segment = sentences[i]
                if len(current) + len(segment) > max_length and current:
                    segments.append(current)
                    current = segment
                else:
                    current += segment
            if current:
                segments.append(current)
            for segment in segments:
                if segment.strip():
                    translated += GoogleTranslator(source='auto', target='zh-CN').translate(segment)

        TRANSLATION_CACHE[text] = translated
        return translated
    except Exception as e:
        log(f"翻译错误: {str(e)}")
        return text

def fetch_html(url, headers=None):
    """获取网页HTML内容"""
    try:
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        log(f"获取HTML错误 {url}: {str(e)}")
        return None

def parse_html_content(html, selectors):
    """解析HTML内容"""
    if not html:
        return []
    soup = BeautifulSoup(html, 'lxml')
    results = []
    for selector in selectors:
        elements = soup.select(selector)
        for elem in elements[:10]:
            title = elem.get_text(strip=True)
            link = elem.get('href', elem.find('a')).get('href', '') if elem.find('a') else ''
            if link and not link.startswith('http'):
                base_url = str(elem.find('a').get('href', '')).rsplit('/', 1)[0] if elem.find('a') else ''
            if title and len(title) > 10:
                results.append({'title': title, 'url': link})
    return results

# ==================== 数据源 ====================

# 中文AI媒体数据源 - 按重要性排序
CHINESE_AI_SOURCES = [
    # 第一优先级：专业AI媒体
    {
        'name': '新智元',
        'url': 'https://www.jiqizhixin.com',
        'priority': 1,
        'type': 'rss'
    },
    {
        'name': '量子位',
        'url': 'https://www.qbitai.com',
        'priority': 1,
        'type': 'rss'
    },
    {
        'name': '机器之心',
        'url': 'https://www.jiqizhixin.com',
        'priority': 1,
        'type': 'html'
    },
    {
        'name': 'AI科技评论',
        'url': 'https://www.aitechtalk.com',
        'priority': 2,
        'type': 'html'
    },

    # 第二优先级：科技媒体AI版块
    {
        'name': '雷锋网AI',
        'url': 'https://www.leiphone.com',
        'priority': 2,
        'type': 'html'
    },
    {
        'name': '智东西',
        'url': 'https://www.zhidx.com',
        'priority': 2,
        'type': 'html'
    },
    {
        'name': '钛媒体AI',
        'url': 'https://www.tmtpost.com/tag/AI',
        'priority': 2,
        'type': 'html'
    },
    {
        'name': '36氪AI',
        'url': 'https://36kr.com/tag/人工智能',
        'priority': 2,
        'type': 'html'
    },
    {
        'name': '虎嗅AI',
        'url': 'https://www.huxiu.com/tag/AI',
        'priority': 2,
        'type': 'html'
    },

    # 第三优先级：技术社区
    {
        'name': 'InfoQ中文',
        'url': 'https://www.infoq.cn/topic/AI',
        'priority': 3,
        'type': 'html'
    },
    {
        'name': 'CSDN AI',
        'url': 'https://www.csdn.net/tag/AI',
        'priority': 3,
        'type': 'html'
    },
    {
        'name': '51CTO AI',
        'url': 'https://www.51cto.com/tag/AI',
        'priority': 3,
        'type': 'html'
    },
    {
        'name': 'OSC AI开源',
        'url': 'https://www.oschina.net/tag/AI',
        'priority': 3,
        'type': 'html'
    },
]

def fetch_chinese_ai_news():
    """获取中文AI资讯 - 增强版"""
    all_news = []

    # 尝试使用RSS获取新智元和量子位
    rss_sources = [
        ("https://www.jiqizhixin.com/rss", "新智元"),
        ("https://www.qbitai.com/feed", "量子位"),
    ]

    for rss_url, source_name in rss_sources:
        try:
            print(f"  📡 {source_name} RSS...", end='', flush=True)
            feed = parse(rss_url)
            items_count = 0
            for entry in feed.entries[:6]:
                title = entry.get('title', '')
                url = entry.get('link', '')
                description = entry.get('description', entry.get('summary', ''))

                # 清理描述
                if description:
                    description = re.sub(r'<[^>]+>', '', description)
                    description = description[:80] + '...' if len(description) > 80 else description

                if title and url:
                    all_news.append({
                        'title': title,
                        'url': url,
                        'description': description,
                        'source': source_name
                    })
                    items_count += 1
            print(f" ✅ {items_count}条")
        except Exception as e:
            print(f" ⚠️")
            log(f"{source_name} RSS获取错误: {str(e)}")

    # 使用HTML解析获取其他中文媒体
    html_sources = [
        ('雷锋网', 'https://www.leiphone.com', 'leiphone-article-title a, .article-title a, h2 a'),
        ('智东西', 'https://www.zhidx.com', 'h2 a, .article-title a, .post-title a'),
        ('钛媒体', 'https://www.tmtpost.com/tag/AI', 'h2 a, .article-title a, .post-title a'),
        ('虎嗅', 'https://www.huxiu.com/tag/AI', 'h2 a, .article-title a'),
        ('InfoQ', 'https://www.infoq.cn/topic/AI', 'h2 a, .article-title a'),
        ('CSDN', 'https://www.csdn.net/tag/AI', 'h2 a, .article-title a'),
    ]

    for source_name, url, selector in html_sources[:4]:  # 限制数量避免超时
        try:
            print(f"  📡 {source_name}...", end='', flush=True)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                articles = soup.select(selector)
                items_count = 0
                for article in articles[:5]:
                    title = article.get_text(strip=True)
                    link = article.get('href', '')
                    if link and not link.startswith('http'):
                        if link.startswith('/'):
                            link = url.rstrip('/') + link
                        else:
                            link = url + '/' + link
                    if title and len(title) > 8 and link:
                        all_news.append({
                            'title': title,
                            'url': link,
                            'description': '',
                            'source': source_name
                        })
                        items_count += 1
                print(f" ✅ {items_count}条")
            else:
                print(f" ⚠️ HTTP {response.status_code}")
        except Exception as e:
            print(f" ⚠️")
            log(f"{source_name}获取错误: {str(e)}")

    return all_news

def fetch_36kr_ai_news():
    """获取36氪AI资讯"""
    news_items = []
    try:
        url = "https://36kr.com/tag/人工智能"
        html = fetch_html(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            articles = soup.select('.article-item-title a, .kr-article-title a, h2 a, h3 a')
            for article in articles[:6]:
                title = article.get_text(strip=True)
                link = article.get('href', '')
                if link and not link.startswith('http'):
                    link = 'https://36kr.com' + link
                if title and len(title) > 10:
                    news_items.append({
                        'title': title,
                        'url': link,
                        'description': '',
                        'source': '36氪'
                    })
    except Exception as e:
        log(f"36氪获取错误: {str(e)}")
    return news_items

def fetch_jiqizhixin_news():
    """获取机器之心资讯"""
    news_items = []
    try:
        url = "https://www.jiqizhixin.com/"
        html = fetch_html(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            articles = soup.select('h2 a, h3 a, .article-title a, .post-title a')
            for article in articles[:6]:
                title = article.get_text(strip=True)
                link = article.get('href', '')
                if link and not link.startswith('http'):
                    link = 'https://www.jiqizhixin.com' + link
                if title and len(title) > 10:
                    news_items.append({
                        'title': title,
                        'url': link,
                        'description': '',
                        'source': '机器之心'
                    })
    except Exception as e:
        log(f"机器之心获取错误: {str(e)}")
    return news_items

def fetch_quantbit_news():
    """获取量子位资讯"""
    news_items = []
    try:
        url = "https://www.qbitai.com/"
        html = fetch_html(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            articles = soup.select('h2 a, h3 a, .entry-title a, .post-title a')
            for article in articles[:8]:
                title = article.get_text(strip=True)
                link = article.get('href', '')
                if link and not link.startswith('http'):
                    link = 'https://www.qbitai.com' + link
                if title and len(title) > 10:
                    news_items.append({
                        'title': title,
                        'url': link,
                        'description': '',
                        'source': '量子位'
                    })
    except Exception as e:
        log(f"量子位获取错误: {str(e)}")
    return news_items

def fetch_venturebeat_ai():
    """获取VentureBeat AI新闻"""
    news_items = []
    try:
        url = "https://venturebeat.com/category/ai/"
        html = fetch_html(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            articles = soup.select('h2 a, h3 a, .article-title a, .post-title a')
            for article in articles[:6]:
                title = article.get_text(strip=True)
                link = article.get('href', '')
                if title:
                    title_cn = translate_to_chinese(title)
                    news_items.append({
                        'title': title_cn,
                        'url': link,
                        'description': '',
                        'source': 'VentureBeat'
                    })
    except Exception as e:
        log(f"VentureBeat获取错误: {str(e)}")
    return news_items

def fetch_techcrunch_ai():
    """获取TechCrunch AI新闻（通过RSS）"""
    news_items = []
    try:
        feed_url = "https://techcrunch.com/category/artificial-intelligence/feed/"
        feed = parse(feed_url)
        for entry in feed.entries[:6]:
            title = entry.get('title', '')
            description = entry.get('description', entry.get('summary', ''))
            url = entry.get('link', '')

            # 清理HTML
            description = re.sub(r'<[^>]+>', '', description)
            description = description[:200] + '...' if len(description) > 200 else description

            # 翻译
            title_cn = translate_to_chinese(title)
            description_cn = translate_to_chinese(description)

            news_items.append({
                'title': title_cn,
                'url': url,
                'description': description_cn,
                'source': 'TechCrunch'
            })
    except Exception as e:
        log(f"TechCrunch获取错误: {str(e)}")
    return news_items

def fetch_verge_ai():
    """获取The Verge AI新闻（通过RSS）"""
    news_items = []
    try:
        feed_url = "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"
        feed = parse(feed_url)
        for entry in feed.entries[:5]:
            title = entry.get('title', '')
            description = entry.get('description', entry.get('summary', ''))
            url = entry.get('link', '')

            description = re.sub(r'<[^>]+>', '', description)
            description = description[:200] + '...' if len(description) > 200 else description

            title_cn = translate_to_chinese(title)
            description_cn = translate_to_chinese(description)

            news_items.append({
                'title': title_cn,
                'url': url,
                'description': description_cn,
                'source': 'The Verge'
            })
    except Exception as e:
        log(f"The Verge获取错误: {str(e)}")
    return news_items

def fetch_rss_feeds():
    """获取RSS订阅源 - 扩展版"""
    news_items = []

    # 英文AI媒体RSS源
    rss_sources = [
        # AI专业媒体
        ("https://www.artificialintelligence-news.com/feed/", "AI-News"),
        ("https://www.aitimes.com/feed/", "AI Times"),
        ("https://syncedreview.com/feed", "Synced"),

        # 科技媒体AI版块
        ("https://feeds.arstechnica.com/arstechnica/technology-lab", "Ars Technica"),
        ("https://www.wired.com/feed/rss/category/ai/index.html", "Wired AI"),
        ("https://www.technologyreview.com/feed/", "MIT Tech Review"),

        # 数据科学媒体
        ("https://towardsdatascience.com/feed", "Towards Data Science"),
        ("https://www.kdnuggets.com/feed", "KDnuggets"),

        # 开发者媒体
        ("https://hackaday.com/blog/feed/", "Hackaday"),
        ("https://www.infoq.com/feed", "InfoQ"),
    ]

    for feed_url, source_name in rss_sources:
        try:
            feed = parse(feed_url)
            for entry in feed.entries[:4]:
                title = entry.get('title', '')
                description = entry.get('description', entry.get('summary', ''))
                url = entry.get('link', '')

                description = re.sub(r'<[^>]+>', '', description)
                description = description[:200] + '...' if len(description) > 200 else description

                title_cn = translate_to_chinese(title)
                description_cn = translate_to_chinese(description)

                news_items.append({
                    'title': title_cn,
                    'url': url,
                    'description': description_cn,
                    'source': source_name
                })
        except Exception as e:
            log(f"{source_name} RSS获取错误: {str(e)}")

    return news_items

def fetch_github_trending():
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
                    'description': translate_to_chinese(repo.get('description', '暂无描述'))
                }
                for repo in repos
            ]
    except Exception as e:
        log(f"GitHub热门项目获取错误: {str(e)}")
    return []

def fetch_huggingface_trending():
    """获取HuggingFace热门模型"""
    try:
        # 按下载量排序
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
                    'description': translate_to_chinese(model.get('description', ''))
                }
                for model in models
            ]
    except Exception as e:
        log(f"HuggingFace获取错误: {str(e)}")
    return []

def fetch_papers_with_code():
    """获取Papers with Code热门论文"""
    try:
        url = "https://paperswithcode.com/api/v1/papers/"
        params = {
            'page_size': 5
        }

        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            papers = response.json().get('results', [])
            return [
                {
                    'title': paper.get('title', ''),
                    'url': f"https://paperswithcode.com/paper/{paper.get('id', '')}",
                    'published': paper.get('published', ''),
                    'description': translate_to_chinese(paper.get('abstract', '')[:150])
                }
                for paper in papers
            ]
    except Exception as e:
        log(f"Papers with Code获取错误: {str(e)}")
    return []

def fetch_reddit_ai():
    """获取Reddit r/MachineLearning 热门帖子"""
    news_items = []
    try:
        url = "https://www.reddit.com/r/MachineLearning/hot.json?limit=8"
        headers = {'User-Agent': 'Mozilla/5.0'}

        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            posts = data.get('data', {}).get('children', [])

            for post in posts[:6]:
                post_data = post.get('data', {})
                title = post_data.get('title', '')
                url = post_data.get('url', '')
                permalink = 'https://reddit.com' + post_data.get('permalink', '')
                selftext = post_data.get('selftext', '')

                # 翻译标题
                title_cn = translate_to_chinese(title)

                # 如果有正文，使用正文作为描述
                if selftext:
                    description = translate_to_chinese(selftext[:100])
                else:
                    description = f"查看讨论: {url[:50]}..."

                news_items.append({
                    'title': title_cn,
                    'url': permalink if permalink else url,
                    'description': description,
                    'source': 'Reddit ML'
                })
    except Exception as e:
        log(f"Reddit获取错误: {str(e)}")
    return news_items

def fetch_hacker_news_ai():
    """获取Hacker News AI相关新闻"""
    news_items = []
    try:
        # 获取Hacker News首页
        url = "https://hacker-news.firebaseio.com/v0/newstories.json?print=pretty"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            item_ids = response.json()[:15]  # 获取前15条

            for item_id in item_ids[:8]:
                try:
                    item_url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json?print=pretty"
                    item_response = requests.get(item_url, timeout=10)

                    if item_response.status_code == 200:
                        item_data = item_response.json()
                        title = item_data.get('title', '')
                        item_url_link = item_data.get('url', '')

                        # 筛选AI相关的
                        title_lower = title.lower()
                        ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'deep learning',
                                       'neural', 'gpt', 'llm', 'chatgpt', 'model', 'openai', 'google ai',
                                       '人工智能', '机器学习', '深度学习']

                        if any(keyword in title_lower for keyword in ai_keywords):
                            title_cn = translate_to_chinese(title)
                            url = item_url_link if item_url_link else f"https://news.ycombinator.com/item?id={item_id}"

                            news_items.append({
                                'title': title_cn,
                                'url': url,
                                'description': '',
                                'source': 'Hacker News'
                            })
                except:
                    continue
    except Exception as e:
        log(f"Hacker News获取错误: {str(e)}")
    return news_items

def fetch_devto_ai():
    """获取Dev.to AI文章"""
    news_items = []
    try:
        url = "https://dev.to/api/articles?tag=artificialintelligence&top=7"
        headers = {'User-Agent': 'Mozilla/5.0'}

        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            articles = response.json()

            for article in articles[:5]:
                title = article.get('title', '')
                url = article.get('url', '')
                description = article.get('description', '')

                title_cn = translate_to_chinese(title)
                description_cn = translate_to_chinese(description[:80]) if description else ''

                news_items.append({
                    'title': title_cn,
                    'url': url,
                    'description': description_cn,
                    'source': 'Dev.to'
                })
    except Exception as e:
        log(f"Dev.to获取错误: {str(e)}")
    return news_items

def categorize_news(item):
    """对新闻进行分类"""
    title = item.get('title', '').lower()
    desc = item.get('description', '').lower()

    if any(word in title for word in ['gpt', 'claude', 'gemini', 'llama', '模型', 'model', 'openai', 'anthropic', 'google']):
        return 'model_releases'
    elif any(word in title for word in ['融资', 'funding', '投资', 'investment', 'ipo', 'unicorn', '亿美元', '亿人民币']):
        return 'funding'
    elif any(word in title for word in ['监管', '政策', 'regulation', 'policy', 'law', '法案', '法规']):
        return 'policy'
    elif any(word in title for word in ['发布', 'launch', 'release', '推出', '产品', 'product', '上线']):
        return 'products'
    else:
        return 'headlines'

# ==================== 主函数 ====================

def fetch_all_ai_news():
    """从所有来源获取AI资讯"""
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
        'huggingface': [],
        'papers': []
    }

    # 中文媒体 - 使用增强版获取函数
    print("📡 获取中文AI媒体（按重要性排序）...")
    cn_items = fetch_chinese_ai_news()
    for item in cn_items:
        category = categorize_news(item)
        all_news[category].append(item)
    print(f"  ✅ 中文媒体共获取 {len(cn_items)} 条\n")

    # 英文媒体（带翻译）
    print("\n📡 获取英文AI媒体（含翻译）...")
    en_sources = [
        ("TechCrunch", fetch_techcrunch_ai),
        ("The Verge", fetch_verge_ai),
        ("VentureBeat", fetch_venturebeat_ai),
        ("RSS订阅源", fetch_rss_feeds),
    ]

    for source_name, fetch_func in en_sources:
        try:
            print(f"  - {source_name}...", end='', flush=True)
            items = fetch_func()
            for item in items:
                category = categorize_news(item)
                all_news[category].append(item)
            print(f" ✅ {len(items)}条")
        except Exception as e:
            print(f" ❌")
            log(f"{source_name}错误: {str(e)}")

    # 开发平台
    print("\n📡 获取开发平台数据...")
    print("  - GitHub热门项目...", end='', flush=True)
    all_news['github_trending'] = fetch_github_trending()
    print(f" ✅ {len(all_news['github_trending'])}个")

    print("  - HuggingFace热门模型...", end='', flush=True)
    all_news['huggingface'] = fetch_huggingface_trending()
    print(f" ✅ {len(all_news['huggingface'])}个")

    print("  - Papers with Code...", end='', flush=True)
    all_news['papers'] = fetch_papers_with_code()
    print(f" ✅ {len(all_news['papers'])}篇")

    # 社区媒体
    print("\n📡 获取社区AI讨论...")
    print("  - Reddit r/MachineLearning...", end='', flush=True)
    reddit_items = fetch_reddit_ai()
    for item in reddit_items:
        category = categorize_news(item)
        all_news[category].append(item)
    print(f" ✅ {len(reddit_items)}条")

    print("  - Hacker News AI...", end='', flush=True)
    hn_items = fetch_hacker_news_ai()
    for item in hn_items:
        category = categorize_news(item)
        all_news[category].append(item)
    print(f" ✅ {len(hn_items)}条")

    print("  - Dev.to AI...", end='', flush=True)
    devto_items = fetch_devto_ai()
    for item in devto_items:
        category = categorize_news(item)
        all_news[category].append(item)
    print(f" ✅ {len(devto_items)}条")

    # 统计
    print(f"\n{'='*60}")
    print(f"📊 获取统计：")
    print(f"  - 头条新闻: {len(all_news['headlines'])} 条")
    print(f"  - 模型发布: {len(all_news['model_releases'])} 条")
    print(f"  - 融资新闻: {len(all_news['funding'])} 条")
    print(f"  - 政策监管: {len(all_news['policy'])} 条")
    print(f"  - 产品发布: {len(all_news['products'])} 条")
    print(f"  - GitHub热门: {len(all_news['github_trending'])} 个")
    print(f"  - HuggingFace: {len(all_news['huggingface'])} 个")
    print(f"  - 热门论文: {len(all_news['papers'])} 篇")
    print(f"{'='*60}\n")

    return generate_content(all_news)

def format_news_item(item):
    """格式化新闻条目"""
    title = item.get('title', '')
    url = item.get('url', '')
    desc = item.get('description', '')
    source = item.get('source', '资讯')

    # 限制摘要在80字以内
    if desc and len(desc) > 80:
        desc = desc[:77] + '...'

    if url:
        if desc:
            return f"- [{title}]({url})\n  > {desc} — *{source}*"
        else:
            return f"- [{title}]({url}) — *{source}*"
    else:
        return f"- {title} — *{source}*"

def generate_content(news_data):
    """生成Markdown内容"""
    date_str = datetime.now().strftime('%Y年%m月%d日')
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    content = f"""# 📊 AI 每日资讯汇总 - {date_str}

> 更新时间：{update_time}

---

## 🔥 今日头条

"""

    # 头条新闻（取前10条）
    if news_data['headlines']:
        for item in news_data['headlines'][:10]:
            content += format_news_item(item) + "\n\n"
    else:
        content += "*暂无最新头条*\n\n"

    # 模型发布
    content += "## 🆕 模型发布\n\n"
    if news_data['model_releases']:
        content += "| 来源 | 模型/产品 | 时间 |\n"
        content += "|------|----------|------|\n"
        for item in news_data['model_releases'][:6]:
            title = item.get('title', '-')[:30]
            source = item.get('source', '资讯')[:12]
            content += f"| {source} | [{title}]({item.get('url', '')}) | {datetime.now().strftime('%m-%d')} |\n"
    else:
        content += "*暂无最新模型发布*\n\n"

    # 产品发布
    content += "\n## 📦 产品发布\n\n"
    if news_data['products']:
        for item in news_data['products'][:6]:
            content += format_news_item(item) + "\n\n"
    else:
        content += "*暂无最新产品发布*\n\n"

    # 融资新闻
    content += "\n## 💰 融资与投资\n\n"
    if news_data['funding']:
        for item in news_data['funding'][:6]:
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

    # 热门论文
    content += "\n## 📚 热门论文\n\n"
    if news_data['papers']:
        for paper in news_data['papers']:
            content += f"- [{paper['title']}]({paper['url']})\n"
            if paper.get('description'):
                content += f"  > {paper['description'][:100]}…\n\n"
            else:
                content += "\n"
    else:
        content += "*暂无热门论文*\n\n"

    # 页脚
    content += """---

## 📡 数据来源

**中文媒体**：36氪、机器之心、量子位
**英文媒体**：TechCrunch、The Verge、VentureBeat、AI-News
**开发平台**：GitHub、HuggingFace、Papers with Code

**翻译服务**：Google Translate（自动翻译，如有错误请以原文为准）

---

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
    archives = sorted(ARCHIVES_DIR.glob("ai-news-*.md"), reverse=True)

    archive_links = ""
    for archive in archives[:10]:
        archive_date = archive.stem.replace('ai-news-', '')
        try:
            formatted_date = datetime.strptime(archive_date, '%Y-%m-%d').strftime('%m月%d日')
            archive_links += f"- [{formatted_date}](archives/{archive.name})\n"
        except:
            archive_links += f"- [{archive_date}](archives/{archive.name})\n"

    readme_content = f"""# 🤖 AI 每日资讯

> 自动收集最新 AI 行业资讯，每日更新

## 📅 最新资讯

**[{datetime.now().strftime('%Y年%m月%d日')}](archives/{TODAY_FILE.name})**

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
- 📚 **热门论文** - Papers with Code最新研究

## 📡 数据来源

**中文媒体**：36氪、机器之心、量子位
**英文媒体**：TechCrunch、The Verge、VentureBeat、AI-News、AI Times
**开发平台**：GitHub、HuggingFace、Papers with Code

## 🔧 技术实现

- **语言**：Python 3
- **爬虫**：Requests + BeautifulSoup + feedparser
- **翻译**：Google Translate API
- **定时任务**：系统 Crontab（每日7:00）
- **自动部署**：Git 推送到 GitHub

---

*自动生成于 {datetime.now().strftime('%Y年%m月%d日 %H:%M')}*
"""
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"✅ README已更新")

def update_archives_index():
    """更新归档索引文件"""
    archives = sorted(ARCHIVES_DIR.glob("ai-news-*.md"), reverse=True)

    index_content = f"""# 📚 AI 每日资讯归档索引

> 自动更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📅 所有资讯（共 {len(archives)} 篇）

"""

    for archive in archives:
        archive_date = archive.stem.replace('ai-news-', '')
        try:
            formatted_date = datetime.strptime(archive_date, '%Y-%m-%d').strftime('%Y年%m月%d日')
            # 读取文件统计各分类数量
            with open(archive, 'r', encoding='utf-8') as f:
                content = f.read()

                # 统计头条新闻（统计 - [标题] 链接格式的数量）
                headlines = len(re.findall(r'^- \[.*?\]\(https?://.*?\)', content, re.MULTILINE))
                # 但要减去其他分类的条目，头条新闻是第一个section
                # 更准确的方法：解析每个section

                # 统计模型发布（查找表格中的行数，排除表头）
                model_rows = len(re.findall(r'^\| .*? \| \[.*?\]\(https?://.*?\)', content, re.MULTILINE))

                # 统计融资新闻（在融资与投资section中的链接数）
                funding_count = 0
                products_count = 0
                policy_count = 0

                # 分割内容按section
                sections = content.split('## ')
                for section in sections:
                    if '🔥 今日头条' in section or '今日头条' in section:
                        # 头条section
                        headlines = min(headlines, 10)  # 限制最多10条
                    elif '💰 融资与投资' in section:
                        funding_count = len(re.findall(r'^- \[.*?\]\(https?://.*?\)', section, re.MULTILINE))
                    elif '📦 产品发布' in section:
                        products_count = len(re.findall(r'^- \[.*?\]\(https?://.*?\)', section, re.MULTILINE))
                    elif '🏛️ 政策与监管' in section:
                        policy_count = len(re.findall(r'^- \[.*?\]\(https?://.*?\)', section, re.MULTILINE))

            stats_parts = []
            if headlines > 0:
                stats_parts.append(f"头条{headlines}条")
            if model_rows > 0:
                stats_parts.append(f"模型{model_rows}个")
            if funding_count > 0:
                stats_parts.append(f"融资{funding_count}条")
            if products_count > 0:
                stats_parts.append(f"产品{products_count}条")
            if policy_count > 0:
                stats_parts.append(f"政策{policy_count}条")

            stats_str = " | ".join(stats_parts) if stats_parts else ""
            index_content += f"- [{formatted_date}](./{archive.name})"
            if stats_str:
                index_content += f" - {stats_str}"
            index_content += "\n"
        except Exception as e:
            index_content += f"- [{archive_date}](./{archive.name})\n"

    index_content += f"""

## 📊 统计信息

- **总资讯数**: {len(archives)} 篇
- **最新更新**: {archives[0].stem.replace('ai-news-', '') if archives else '无'}
- **最早更新**: {archives[-1].stem.replace('ai-news-', '') if archives else '无'}

---

*本文件由 [daily-ai-news](https://github.com/chenjingxiong/daily-ai-news) 自动生成*
"""

    with open(ARCHIVES_DIR / "README.md", 'w', encoding='utf-8') as f:
        f.write(index_content)
    print(f"✅ 归档索引已更新：{ARCHIVES_DIR / 'README.md'}")

def commit_to_github():
    """提交更改到GitHub"""
    os.chdir(PROJECT_DIR)

    if not (PROJECT_DIR / ".git").exists():
        print("⚠️  Git仓库未初始化")
        return

    run_command("git add .")
    print("✅ 文件已暂存")

    status = run_command("git status --porcelain", check=False)
    if not status.stdout.strip():
        print("ℹ️  没有新的更改")
        return

    date_str = datetime.now().strftime('%Y-%m-%d')
    commit_msg = f"🤖 AI资讯更新 - {date_str}"
    run_command(f'git commit -m "{commit_msg}"')
    print(f"✅ 已提交：{commit_msg}")

    result = run_command("git push")
    if result.returncode == 0:
        print("✅ 已推送到GitHub")
    else:
        print("⚠️  推送失败 - 请检查GitHub认证")

def main():
    """主函数"""
    log("=== 开始获取AI资讯 ===")

    print("\n" + "="*60)
    print("🤖 AI 每日资讯获取器（多数据源 + 自动翻译）")
    print("="*60)

    try:
        # 获取资讯
        content = fetch_all_ai_news()

        # 保存Markdown
        save_markdown(content)

        # 更新README
        update_readme()

        # 更新归档索引
        update_archives_index()

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
