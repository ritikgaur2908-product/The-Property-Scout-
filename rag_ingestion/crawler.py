import json
import logging
from typing import Dict, List
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def crawl_blrexplorer_sentiment() -> List[Dict[str, str]]:
    """
    Crawls 105 Bengaluru localities with real citizen quotes and sentiment summaries
    from blrexplorer.littlemadcow.xyz (the public explorer referenced in the project spec).
    """
    url = "https://blrexplorer.littlemadcow.xyz/sentiment.json"
    logger.info(f"Crawling public resident sentiment from {url}...")
    documents = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Retrieved sentiment records for {len(data)} localities.")

        for item in data:
            locality = item.get("name", "").strip()
            if not locality:
                continue

            summary = item.get("summary", "")
            label = item.get("label", "Neutral")
            quotes = item.get("quotes", [])
            total_mentions = item.get("total", 0)

            # 1. Document for neighborhood resident summary & sentiment
            if summary:
                documents.append({
                    "url": f"https://blrexplorer.littlemadcow.xyz/#{locality.lower().replace(' ', '-')}",
                    "locality": locality,
                    "text": (
                        f"Resident feedback for {locality}, Bengaluru (Overall Sentiment: {label}, based on {total_mentions} public discussions): "
                        f"{summary}"
                    ),
                    "source_type": "community_forum"
                })

            # 2. Document for real citizen quotes
            for idx, quote in enumerate(quotes, start=1):
                clean_quote = quote.strip()
                if len(clean_quote) > 25:
                    documents.append({
                        "url": f"https://blrexplorer.littlemadcow.xyz/#{locality.lower().replace(' ', '-')}-quote-{idx}",
                        "locality": locality,
                        "text": f"Resident observation in {locality}: \"{clean_quote}\"",
                        "source_type": "community_forum"
                    })

    except Exception as e:
        logger.error(f"Failed crawling blrexplorer sentiment: {e}")

    return documents


def crawl_blrexplorer_geojson() -> List[Dict[str, str]]:
    """
    Crawls real civic infrastructure and livability data (AQI, hospitals, schools,
    transit, supermarkets) from blrexplorer GeoJSON.
    """
    url = "https://blrexplorer.littlemadcow.xyz/localities_top50.geojson"
    logger.info(f"Crawling civic metrics and factors from {url}...")
    documents = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        geo_data = resp.json()
        features = geo_data.get("features", [])
        logger.info(f"Retrieved GeoJSON metrics for {len(features)} localities.")

        for feat in features:
            props = feat.get("properties", {})
            locality = props.get("name", "").strip()
            if not locality:
                continue

            overall_score = props.get("overall_score")
            factors = props.get("factors", {})
            raw = props.get("raw", {})

            # Format real civic and accessibility metrics
            metrics_text = (
                f"Civic Infrastructure & Livability Profile for {locality}, Bengaluru (Livability Score: {overall_score}/10): "
                f"Air Quality Index (AQI): {raw.get('aqi', 'N/A')}, Average Temperature: {raw.get('temperature_c', 'N/A')}°C. "
                f"Nearby Healthcare & Education: {raw.get('hospitals', 0)} hospitals, {raw.get('schools', 0)} schools within access radius. "
                f"Retail & Transit: {raw.get('supermarkets', 0)} supermarkets, {raw.get('restaurants', 0)} dining spots, "
                f"{raw.get('metro_stations', 0)} metro stations, and {raw.get('bus_stops', 0)} BMTC bus stops."
            )

            documents.append({
                "url": f"https://blrexplorer.littlemadcow.xyz/#{locality.lower().replace(' ', '-')}-civic",
                "locality": locality,
                "text": metrics_text,
                "source_type": "civic_data"
            })

    except Exception as e:
        logger.error(f"Failed crawling blrexplorer GeoJSON: {e}")

    return documents


def crawl_citizen_matters() -> List[Dict[str, str]]:
    """
    Crawls real civic news and infrastructure reporting from Citizen Matters Bengaluru.
    """
    url = "https://citizenmatters.in/city/bengaluru/"
    logger.info(f"Crawling civic articles from {url}...")
    documents = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract articles
        articles = soup.find_all("article")
        for article in articles[:10]:
            heading = article.find(["h2", "h3"])
            title = heading.get_text(strip=True) if heading else ""
            link_tag = article.find("a", href=True)
            article_url = link_tag["href"] if link_tag else url
            excerpt = article.find(["p", "div", "section"])
            body_text = excerpt.get_text(separator=" ", strip=True) if excerpt else ""

            if title and len(body_text) > 50:
                documents.append({
                    "url": article_url,
                    "locality": "Bengaluru",
                    "text": f"{title}\n{body_text}",
                    "source_type": "news_and_civic"
                })

        if not documents:
            # Fallback to whole page body text if article tags are structured differently
            for s in soup(["script", "style", "nav", "footer", "header"]):
                s.extract()
            text = soup.get_text(separator=" ", strip=True)
            documents.append({
                "url": url,
                "locality": "Bengaluru",
                "text": text[:3000],
                "source_type": "news_and_civic"
            })

    except Exception as e:
        logger.error(f"Failed crawling Citizen Matters: {e}")

    return documents


def crawl_all_public_sources() -> List[Dict[str, str]]:
    """
    Crawls 100% real public public sources (blrexplorer sentiment quotes, GeoJSON civic metrics,
    and Citizen Matters news) covering all 100+ Bengaluru localities.
    """
    all_docs = []

    # 1. Real Citizen Sentiment & Quotes (105 Localities)
    sentiment_docs = crawl_blrexplorer_sentiment()
    all_docs.extend(sentiment_docs)

    # 2. Real Civic Livability Metrics (57 Localities)
    geo_docs = crawl_blrexplorer_geojson()
    all_docs.extend(geo_docs)

    # 3. Live Civic Journalism (Citizen Matters Bengaluru)
    news_docs = crawl_citizen_matters()
    all_docs.extend(news_docs)

    logger.info(f"Total real public documents collected: {len(all_docs)}")
    return all_docs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    docs = crawl_all_public_sources()
    print(f"Crawled {len(docs)} real public documents from public web sources.")
