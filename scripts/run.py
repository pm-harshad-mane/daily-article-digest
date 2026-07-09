import argparse
import logging
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from config_loader import filter_config, load_config
from digest_writer import update_daily_digest
from discover_articles import discover_article_urls
from extract_article import extract_article
from file_store import save_article_summary
from llm_client import OpenAIClient
from state_store import StateStore
from summarize_article import list_items_from_section, summarize_article
from utils import ensure_directory, format_run_id, normalize_url, now_in_timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local article monitoring runner.")
    parser.add_argument("--config", default="config/websites.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--website")
    parser.add_argument("--section")
    parser.add_argument("--max-articles", type=int)
    return parser.parse_args()


def setup_logging(run_date: str) -> logging.Logger:
    ensure_directory(Path("logs"))
    log_path = Path("logs") / f"{run_date}.log"
    logger = logging.getLogger("article_monitor")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(stream_handler)

    return logger


def ensure_project_directories(dry_run: bool) -> None:
    paths = ["config", "scripts", "logs"]
    if not dry_run:
        paths.extend(["state", "outputs", "digests/daily"])
    for path in paths:
        ensure_directory(Path(path))


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Accept-Language": "en-US,en;q=0.9"})
    return session


def main() -> int:
    args = parse_args()
    load_dotenv()
    ensure_project_directories(args.dry_run)

    config = load_config(args.config)
    config = filter_config(config, args.website, args.section)
    settings = config["settings"]

    started_at = now_in_timezone(settings["output_timezone"])
    run_id = format_run_id(started_at)
    run_date = started_at.date().isoformat()
    logger = setup_logging(run_date)
    state = StateStore("state", initialize_missing=not args.dry_run)
    session = build_session()

    logger.info("Article Monitor started: %s", started_at.isoformat())
    logger.info("Loaded config: %s", args.config)
    logger.info("Loaded state files from state/")

    llm_client = None
    if not args.dry_run:
        llm_client = OpenAIClient(settings["llm_model"])

    processed_articles: list[dict] = []
    articles_failed = 0
    new_articles_found = 0
    sections_processed = 0
    visited_this_run = state.all_visited_urls()
    errors: list[str] = []

    for website in config["websites"]:
        for section in website["sections"]:
            sections_processed += 1
            logger.info("")
            logger.info("Processing %s / %s", website["name"], section["name"])

            try:
                discovered_urls = discover_article_urls(section, website, settings, session, logger)
            except Exception as exc:
                articles_failed += 1
                errors.append(f"Discovery failed for {website['key']}/{section['key']}: {exc}")
                logger.exception("Discovery failed for %s / %s: %s", website["name"], section["name"], exc)
                continue

            skipped_count = 0
            selected_urls = []
            max_articles = args.max_articles or section.get(
                "max_articles_per_run",
                settings["default_max_articles_per_run"],
            )

            for discovered_url in discovered_urls:
                normalized = normalize_url(discovered_url, website["base_url"])
                if normalized in visited_this_run or state.was_visited(website["key"], section["key"], normalized):
                    skipped_count += 1
                    continue
                selected_urls.append(normalized)
                if len(selected_urls) >= max_articles:
                    break

            logger.info("Skipped %s already visited URLs", skipped_count)
            logger.info("Selected %s new articles", len(selected_urls))
            new_articles_found += len(selected_urls)

            if args.dry_run:
                for url in selected_urls:
                    logger.info("Would process: %s", url)
                continue

            for index, article_url in enumerate(selected_urls, start=1):
                try:
                    article = extract_article(article_url, settings, session)
                    logger.info("[%s/%s] Extracting: %s", index, len(selected_urls), article["title"])

                    summary_markdown, summary_sections = summarize_article(article, llm_client)
                    counter = state.peek_next_counter(website["key"], section["key"])
                    output_file = save_article_summary(
                        article=article,
                        website=website,
                        section=section,
                        counter=counter,
                        processed_at=started_at.isoformat(),
                        summary_markdown=summary_markdown,
                    )
                    state.commit_counter(website["key"], section["key"], counter)

                    normalized_url = normalize_url(article["url"], website["base_url"])
                    state.mark_visited(
                        website_key=website["key"],
                        section_key=section["key"],
                        normalized_url=normalized_url,
                        title=article["title"],
                        processed_at=started_at.isoformat(),
                        output_file=output_file,
                    )
                    visited_this_run.add(normalized_url)

                    processed_articles.append(
                        {
                            "title": article["title"],
                            "url": article["url"],
                            "publication_date": article.get("publication_date"),
                            "website_name": website["name"],
                            "section_name": section["name"],
                            "output_file": output_file,
                            "companies": list_items_from_section(summary_sections["Companies Mentioned"]),
                            "key_people": list_items_from_section(summary_sections["Key People Mentioned"]),
                            "topic_tags": list_items_from_section(summary_sections["Topic Tags"]),
                        }
                    )
                    logger.info("Saved: %s", output_file)
                except Exception as exc:
                    articles_failed += 1
                    errors.append(f"Article failed for {article_url}: {exc}")
                    logger.exception("Failed processing article %s: %s", article_url, exc)

    digest_path = ""
    if not args.dry_run and processed_articles:
        digest_path = update_daily_digest(
            run_date=run_date,
            run_id=run_id,
            processed_articles=processed_articles,
            failed_articles=articles_failed,
        )
        logger.info("Daily digest updated: %s", digest_path)

    completed_at = now_in_timezone(settings["output_timezone"])
    if not args.dry_run:
        run_entry = {
            "run_id": run_id,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "websites_processed": len(config["websites"]),
            "sections_processed": sections_processed,
            "new_articles_found": new_articles_found,
            "articles_processed": len(processed_articles),
            "articles_failed": articles_failed,
            "errors": errors,
        }
        state.append_run_history(run_entry)
        logger.info("State updated successfully")
    else:
        logger.info("Dry run completed without writing outputs or state")
    logger.info(
        "Run completed: %s articles processed, %s failed",
        len(processed_articles),
        articles_failed,
    )
    logger.info("")
    logger.info("Review changes with:")
    logger.info("  git status")
    logger.info("  git diff")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
