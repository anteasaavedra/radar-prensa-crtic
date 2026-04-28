import logging
import time
from datetime import datetime
from urllib.parse import urlparse
import requests
from app.config import (
    SEARCH_API_KEY,
    SEARCH_API_PROVIDER,
    GOOGLE_PSE_CX,
    KEYWORDS,
    TIMEZONE,
)

logger = logging.getLogger("radar_prensa.search")

# Segundos de pausa entre llamadas a la API para no sobrepasar rate limits
REQUEST_DELAY = 1.5


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _build_result(title: str, url: str, snippet: str, published, keyword: str, source: str) -> dict:
    return {
        "titulo": title,
        "url": url,
        "snippet": snippet,
        "fecha_publicacion": published,
        "keyword": keyword,
        "medio": source or _extract_domain(url),
        "fecha_deteccion": datetime.now().strftime("%Y-%m-%d"),
    }


# ── SerpAPI ────────────────────────────────────────────────────────────────────

def _search_serpapi(keyword: str) -> list[dict]:
    if not SEARCH_API_KEY:
        logger.warning("SEARCH_API_KEY no configurada para SerpAPI")
        return []

    params = {
        "q": keyword,
        "hl": "es",
        "gl": "cl",
        "num": 10,
        "api_key": SEARCH_API_KEY,
        "tbm": "nws",
    }
    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error("SerpAPI error para '%s': %s", keyword, e)
        return []

    results = []
    for item in data.get("news_results", []):
        results.append(_build_result(
            title=item.get("title", ""),
            url=item.get("link", ""),
            snippet=item.get("snippet", ""),
            published=item.get("date"),
            keyword=keyword,
            source=item.get("source", ""),
        ))
    return results


# ── NewsAPI ────────────────────────────────────────────────────────────────────

def _search_newsapi(keyword: str) -> list[dict]:
    if not SEARCH_API_KEY:
        logger.warning("SEARCH_API_KEY no configurada para NewsAPI")
        return []

    params = {
        "q": keyword,
        "language": "es",
        "sortBy": "publishedAt",
        "pageSize": 10,
        "apiKey": SEARCH_API_KEY,
    }
    try:
        resp = requests.get("https://newsapi.org/v2/everything", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error("NewsAPI error para '%s': %s", keyword, e)
        return []

    results = []
    for item in data.get("articles", []):
        published = item.get("publishedAt", "")[:10] if item.get("publishedAt") else None
        source_name = item.get("source", {}).get("name", "")
        results.append(_build_result(
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("description", ""),
            published=published,
            keyword=keyword,
            source=source_name,
        ))
    return results


# ── Google Programmable Search Engine ─────────────────────────────────────────

def _search_googlepse(keyword: str) -> list[dict]:
    if not SEARCH_API_KEY or not GOOGLE_PSE_CX:
        logger.warning("SEARCH_API_KEY o GOOGLE_PSE_CX no configurados")
        return []

    params = {
        "key": SEARCH_API_KEY,
        "cx": GOOGLE_PSE_CX,
        "q": keyword,
        "num": 10,
        "lr": "lang_es",
        "gl": "cl",
    }
    try:
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1", params=params, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error("Google PSE error para '%s': %s", keyword, e)
        return []

    results = []
    for item in data.get("items", []):
        pagemap = item.get("pagemap", {})
        metatags = pagemap.get("metatags", [{}])[0]
        published = metatags.get("article:published_time", "")[:10] or None
        results.append(_build_result(
            title=item.get("title", ""),
            url=item.get("link", ""),
            snippet=item.get("snippet", ""),
            published=published,
            keyword=keyword,
            source=_extract_domain(item.get("link", "")),
        ))
    return results


# ── Dispatcher ─────────────────────────────────────────────────────────────────

_PROVIDERS = {
    "serpapi": _search_serpapi,
    "newsapi": _search_newsapi,
    "googlepse": _search_googlepse,
}


def search_keyword(keyword: str) -> list[dict]:
    fn = _PROVIDERS.get(SEARCH_API_PROVIDER.lower())
    if fn is None:
        logger.error("Proveedor desconocido: %s", SEARCH_API_PROVIDER)
        return []
    return fn(keyword)


def run_daily_search() -> list[dict]:
    """Ejecuta búsqueda para todos los keywords. Retorna lista de resultados sin deduplicar."""
    all_results: list[dict] = []
    seen_urls: set[str] = set()

    for kw in KEYWORDS:
        logger.info("Buscando: %s", kw)
        results = search_keyword(kw)
        for r in results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(r)
        time.sleep(REQUEST_DELAY)

    logger.info("Búsqueda completada: %d resultados únicos", len(all_results))
    return all_results
