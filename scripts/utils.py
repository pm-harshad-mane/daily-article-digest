import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser


TRACKING_QUERY_PREFIXES = (
    "utm_",
    "fbclid",
    "gclid",
    "mc_",
    "oly_",
    "vero_",
)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen = set()
    ordered = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def normalize_url(url: str, base_url: str | None = None) -> str:
    candidate = urljoin(base_url, url) if base_url else url
    parsed = urlparse(candidate.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    path = re.sub(r"/{2,}", "/", path)
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    ]
    query = urlencode(filtered_query, doseq=True)
    normalized = parsed._replace(
        scheme=scheme,
        netloc=netloc,
        path=path,
        query=query,
        fragment="",
    )
    return urlunparse(normalized)


def slugify(value: str, max_length: int = 80) -> str:
    slug = value.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:max_length].rstrip("-") or "article"


def now_in_timezone(timezone_name: str) -> datetime:
    return datetime.now(ZoneInfo(timezone_name))


def format_run_id(dt: datetime) -> str:
    return dt.isoformat().replace(":", "-")


def normalize_publication_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        return date_parser.parse(value).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return value.strip()


def same_domain(url: str, base_url: str) -> bool:
    url_host = urlparse(url).netloc.lower()
    base_host = urlparse(base_url).netloc.lower()
    return url_host == base_host or url_host.endswith(f".{base_host}")


def collect_top_tags(tag_lists: Iterable[list[str]], limit: int = 5) -> list[str]:
    counter = Counter()
    for tags in tag_lists:
        counter.update([tag.strip() for tag in tags if tag.strip()])
    return [item for item, _count in counter.most_common(limit)]

