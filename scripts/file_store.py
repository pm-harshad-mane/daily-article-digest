from pathlib import Path

from utils import ensure_directory, slugify


def save_article_summary(
    article: dict,
    website: dict,
    section: dict,
    counter: int,
    processed_at: str,
    summary_markdown: str,
) -> str:
    output_dir = Path(website["output_folder"]) / section["key"]
    ensure_directory(output_dir)

    filename = f"{counter:04d}_{slugify(article['title'])}.md"
    output_path = output_dir / filename
    output_path.write_text(
        build_article_markdown(article, website, section, processed_at, summary_markdown),
        encoding="utf-8",
    )
    return output_path.as_posix()


def build_article_markdown(
    article: dict,
    website: dict,
    section: dict,
    processed_at: str,
    summary_markdown: str,
) -> str:
    image_lines = article.get("image_urls") or []
    images_block = "\n".join(f"- {url}" for url in image_lines) if image_lines else "- None"

    return (
        f"# {article['title']}\n\n"
        f"**Source:** {website['name']}  \n"
        f"**Section:** {section['name']}  \n"
        f"**URL:** {article['url']}  \n"
        f"**Publication Date:** {article.get('publication_date') or 'Unknown'}  \n"
        f"**Author:** {article.get('author') or 'Unknown'}  \n"
        f"**Processed Date:** {processed_at}  \n\n"
        "---\n\n"
        f"{summary_markdown.strip()}\n\n"
        "## Image Links\n\n"
        f"{images_block}\n"
    )
