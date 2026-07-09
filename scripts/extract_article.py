import json
from urllib.parse import urljoin

import requests
import trafilatura
from bs4 import BeautifulSoup

from utils import normalize_publication_date, unique_preserve_order


def extract_article(url: str, settings: dict, session: requests.Session) -> dict:
    response = session.get(
        url,
        timeout=settings["request_timeout_seconds"],
        headers={"User-Agent": settings["user_agent"]},
    )
    response.raise_for_status()

    html = response.text
    soup = BeautifulSoup(html, "lxml")
    extracted = trafilatura.extract(
        html,
        url=url,
        output_format="json",
        with_metadata=True,
        include_images=True,
        include_links=False,
    )

    if not extracted:
        raise ValueError("Trafilatura could not extract article content.")

    payload = json.loads(extracted)
    text = (payload.get("text") or "").strip()
    minimum_characters = int(settings.get("minimum_article_characters", 500))
    if len(text) < minimum_characters:
        raise ValueError(f"Article text too short after extraction ({len(text)} chars).")

    title = first_non_empty(
        payload.get("title"),
        meta_content(soup, "property", "og:title"),
        soup.title.string.strip() if soup.title and soup.title.string else "",
        text_from_first(soup, "h1"),
    )
    publication_date = normalize_publication_date(
        first_non_empty(
            payload.get("date"),
            meta_content(soup, "property", "article:published_time"),
            meta_content(soup, "name", "pubdate"),
            meta_content(soup, "name", "publish_date"),
            time_datetime(soup),
        )
    )
    author = first_non_empty(
        payload.get("author"),
        meta_content(soup, "name", "author"),
        meta_content(soup, "property", "article:author"),
    )

    image_urls = collect_image_urls(soup, url, payload)

    return {
        "title": title or url,
        "url": url,
        "publication_date": publication_date,
        "author": author,
        "text": text,
        "image_urls": image_urls,
        "raw_metadata": payload,
    }


def collect_image_urls(soup: BeautifulSoup, article_url: str, payload: dict) -> list[str]:
    images = []
    if payload.get("image"):
        images.append(urljoin(article_url, payload["image"]))

    og_image = meta_content(soup, "property", "og:image")
    if og_image:
        images.append(urljoin(article_url, og_image))

    for image in soup.find_all("img", src=True):
        images.append(urljoin(article_url, image.get("src", "")))

    return unique_preserve_order([image for image in images if image])


def meta_content(soup: BeautifulSoup, attr_name: str, attr_value: str) -> str:
    tag = soup.find("meta", attrs={attr_name: attr_value})
    if tag:
        return (tag.get("content") or "").strip()
    return ""


def time_datetime(soup: BeautifulSoup) -> str:
    tag = soup.find("time")
    if tag:
        return (tag.get("datetime") or tag.get_text(strip=True) or "").strip()
    return ""


def text_from_first(soup: BeautifulSoup, selector: str) -> str:
    tag = soup.select_one(selector)
    return tag.get_text(" ", strip=True) if tag else ""


def first_non_empty(*values: str | None) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""
