from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from utils import normalize_url, same_domain, unique_preserve_order


EXCLUDED_PATTERNS = (
    "/tag/",
    "/author/",
    "/category/",
    "/content-studio/",
    "/daily-news-roundup/",
    "/data-driven-thinking/",
    "/go/",
    "/page/",
    "/about",
    "/contact",
    "/privacy",
    "/terms",
    "/newsletter",
    "/events",
    "#",
    "mailto:",
    "javascript:",
)


def discover_article_urls(section: dict, website: dict, settings: dict, session: requests.Session, logger) -> list[str]:
    response = session.get(
        section["url"],
        timeout=settings["request_timeout_seconds"],
        headers={"User-Agent": settings["user_agent"]},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    candidates = []
    section_url = normalize_url(section["url"], website["base_url"])
    article_anchors = soup.select("h1 a.link-post[href], h2 a.link-post[href], h3 a.link-post[href], h4 a.link-post[href]")
    anchors = article_anchors if article_anchors else soup.find_all("a", href=True)

    for anchor in anchors:
        href = anchor.get("href", "").strip()
        if not href:
            continue
        if any(pattern in href.lower() for pattern in EXCLUDED_PATTERNS):
            continue

        absolute_url = normalize_url(href, website["base_url"])
        parsed = urlparse(absolute_url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if absolute_url == section_url:
            continue
        if not same_domain(absolute_url, website["base_url"]):
            continue
        if not looks_like_article_url(absolute_url, website["base_url"]):
            continue

        candidates.append(absolute_url)

    deduped = unique_preserve_order(candidates)
    logger.info(
        "Discovered %s candidate article URLs for %s / %s",
        len(deduped),
        website["name"],
        section["name"],
    )
    return deduped


def looks_like_article_url(url: str, base_url: str) -> bool:
    parsed = urlparse(url)
    base_host = urlparse(base_url).netloc.lower()
    if parsed.netloc.lower() != base_host:
        return False

    path = parsed.path.strip("/")
    if not path:
        return False

    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        return False

    first_segment = parts[0].lower()
    if first_segment in {
        "tag",
        "author",
        "category",
        "topic",
        "topics",
        "news",
        "latest",
        "content-studio",
        "daily-news-roundup",
        "data-driven-thinking",
        "go",
    }:
        return False

    last_segment = parts[-1].lower()
    if last_segment in {"amp"}:
        return False

    return True
