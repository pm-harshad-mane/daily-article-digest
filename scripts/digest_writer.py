from collections import defaultdict
from pathlib import Path

from summarize_article import list_items_from_section
from utils import collect_top_tags, ensure_directory


def update_daily_digest(run_date: str, run_id: str, processed_articles: list[dict], failed_articles: int) -> str:
    digest_dir = Path("digests/daily")
    ensure_directory(digest_dir)
    digest_path = digest_dir / f"{run_date}.md"

    section_lines = [
        f"## Run Summary ({run_id})",
        "",
        f"- Run ID: {run_id}",
        f"- New articles processed: {len(processed_articles)}",
        f"- Failed articles: {failed_articles}",
        "",
        "## Articles Processed",
        "",
    ]

    by_section: dict[str, list[dict]] = defaultdict(list)
    for article in processed_articles:
        key = f"{article['website_name']} / {article['section_name']}"
        by_section[key].append(article)

    for grouping, articles in by_section.items():
        section_lines.append(f"### {grouping}")
        section_lines.append("")
        for index, article in enumerate(articles, start=1):
            tags = ", ".join(article["topic_tags"]) if article["topic_tags"] else "None"
            people = ", ".join(article["key_people"]) if article["key_people"] else "None"
            section_lines.append(
                f"{index}. [{article['title']}](../../{article['output_file']})"
            )
            section_lines.append(f"   - URL: {article['url']}")
            section_lines.append(
                f"   - Publication Date: {article.get('publication_date') or 'Unknown'}"
            )
            section_lines.append(f"   - Key People: {people}")
            section_lines.append(f"   - Topic Tags: {tags}")
            section_lines.append("")

    top_tags = collect_top_tags([article["topic_tags"] for article in processed_articles], limit=5)
    companies = sorted(
        {
            company
            for article in processed_articles
            for company in article["companies"]
            if company
        }
    )
    people = sorted(
        {
            person
            for article in processed_articles
            for person in article["key_people"]
            if person
        }
    )

    section_lines.extend(["## Key Themes", ""])
    if top_tags:
        section_lines.extend([f"- {tag}" for tag in top_tags])
    else:
        section_lines.append("- None")

    section_lines.extend(["", "## Companies Mentioned Today", ""])
    if companies:
        section_lines.extend([f"- {company}" for company in companies])
    else:
        section_lines.append("- None")

    section_lines.extend(["", "## Key People Mentioned Today", ""])
    if people:
        section_lines.extend([f"- {person}" for person in people])
    else:
        section_lines.append("- None")

    header = f"# Daily Article Digest - {run_date}\n\n"
    new_block = "\n".join(section_lines).rstrip() + "\n"

    if digest_path.exists():
        existing = digest_path.read_text(encoding="utf-8").rstrip()
        if not existing.startswith(f"# Daily Article Digest - {run_date}"):
            existing = header.rstrip()
        content = f"{existing}\n\n---\n\n{new_block}"
    else:
        content = header + new_block

    digest_path.write_text(content, encoding="utf-8")
    return digest_path.as_posix()
