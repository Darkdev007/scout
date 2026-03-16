import httpx
import os
import re
import feedparser
from langchain.tools import tool
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

AFRICAN_FEEDS = {
    "techpoint":        "https://techpoint.africa/feed",
    "nairametrics":     "https://nairametrics.com/feed",
    "disrupt_africa":   "https://disruptafrica.com/feed",
    "techcrunch_africa": "https://techcrunch.com/tag/africa/feed",
}

gnews_api = os.environ.get("GNEWS_API")

@tool
def get_wikipedia_summary(topic: str) -> str:
    """
    Get background context on a company, person, or concept.
    Use this as the first tool for any research query to establish
    foundational context before searching for news.
    """
    headers = {"User-Agent": "Scout/1.0 (research agent; tobilobaayodele23@gmail.com)"}
    
    variations = [
        topic,                                    
        topic.title(),                            
        topic.title().replace(" ", "_"),          
        topic.split()[0].title(),                 
        topic.replace(" ", "_"),                  
        topic.title().split()[0],                 
    ]
    
    # deduplicate while preserving order
    seen = set()
    unique_variations = []
    for v in variations:
        if v not in seen:
            seen.add(v)
            unique_variations.append(v)
    
    for variation in unique_variations:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{variation.replace(' ', '_')}"
        response = httpx.get(url, timeout=10, follow_redirects=True, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("type") == "disambiguation":
                continue
            return f"Title: {data['title']}\n\n{data['extract']}"
    
    return f"NO_RESULTS: No Wikipedia page found for '{topic}'. Scout will rely on news sources for context."

@tool
def get_global_news(query: str, days_back: int = 30, max_articles: int = 5) -> str:
    """
    Search for recent global news articles on a company, topic, or market.
    Use for international companies or broad market queries.
    Default search window is 30 days. Increase days_back to 90 if results are empty.
    If results are still empty, try a broader query term like the company's sector.
    """
    # calculate date range

    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    params = {
        "q": query,
        "lang": "en",
        "max": max_articles,
        "sortby": "publishedAt",
        "from": from_date,
        "apikey": gnews_api
    }
    
    response = httpx.get(
        "https://gnews.io/api/v4/search",
        params=params,
        timeout=10
    )
    
    if response.status_code != 200:
        return f"ERROR: GNews returned status {response.status_code}"
    
    data = response.json()
    articles = data.get("articles", [])
    
    if not articles:
        return f"NO_RESULTS: No news found for '{query}' in the last {days_back} days. Try broader search terms."
    
    results = []
    for a in articles:
        results.append(
            f"• {a['title']}\n"
            f"  Source: {a['source']['name']} | {a['publishedAt'][:10]}\n"
            f"  {a['description']}\n"
        )
    
    return f"Found {len(articles)} articles for '{query}':\n\n" + "\n".join(results)


def clean_summary(html: str) -> str:
    text = re.sub(r'<[^>]+>', '', html)
    text = re.sub(r'The post .+ appeared first on .+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

@tool
def get_african_news(query: str) -> str:
    """
    Get the latest news from African tech and business sources.
    Use for Nigerian, Kenyan, Ghanaian companies or African market
    queries. Returns recent articles only — not historical.
    Use get_global_news for older or international coverage.
    """
    query_lower = query.lower()
    results = []

    for source, url in AFRICAN_FEEDS.items():
        try:
            feed = feedparser.parse(url)

            for entry in feed.entries:
                title = entry.get("title", "").replace('\xa0', ' ')
                summary = clean_summary(entry.get("summary", ""))
                published = entry.get("published", "")[:16]
                link = entry.get("link", "")

                keywords = [w for w in query_lower.split() if len(w) > 3]  # skip short words
                if any(kw in title.lower() or kw in summary.lower() for kw in keywords):
                    results.append(
                        f"• [{source}] {title}\n"
                        f"  {published}\n"
                        f"  {summary[:200]}\n"
                        f"  {link}\n"
                    )

        except Exception as e:
            continue

    if not results:
        return f"NO_RESULTS: '{query}' not in recent African news. Scout will fall back to global sources."

    return f"Found {len(results)} recent African articles for '{query}':\n\n" + "\n".join(results)

@tool
def get_exchange_rates(base_currency: str = "USD") -> str:
    """
    Get current foreign exchange rates. Always include this tool
    for any African market query, investment analysis, or when
    the user asks about currency, money, or cross-border finance.
    """
    response = httpx.get(
        f"https://open.er-api.com/v6/latest/{base_currency.upper()}",
        timeout=10
    )

    if response.status_code != 200:
        return f"ERROR: ExchangeRate API returned status {response.status_code}"

    data = response.json()

    if data.get("result") != "success":
        return f"ERROR: {data.get('error-type', 'Unknown error')}"

    rates = data["rates"]
    last_updated = data["time_last_update_utc"]

    key_currencies = ["NGN", "USD", "GBP", "EUR", "GHS", "KES", "ZAR"]

    def format_rate(value: float) -> str:
        if value >= 1:
            return f"{value:,.2f}"
        elif value >= 0.01:
            return f"{value:.4f}"
        else:
            return f"{value:.6f}"  # handles tiny values like NGN/USD

    lines = [f"Exchange rates (base: {base_currency.upper()}):\n"]
    for currency in key_currencies:
        if currency in rates and currency != base_currency.upper():
            lines.append(f"  {currency}: {format_rate(rates[currency])}")

    lines.append(f"\nLast updated: {last_updated}")

    return "\n".join(lines)

