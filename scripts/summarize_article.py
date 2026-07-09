SECTION_HEADINGS = [
    "Summary",
    "Problem / Workflow Challenge",
    "Solution / Key Development",
    "Companies Mentioned",
    "Key People Mentioned",
    "Why This Matters for My Work",
    "Topic Tags",
]
MAX_ARTICLE_TEXT_CHARS = 20000


def summarize_article(article: dict, llm_client) -> tuple[str, dict]:
    prompt = build_prompt(article)
    markdown = llm_client.summarize(prompt)
    sections = parse_markdown_sections(markdown)
    return markdown, sections


def build_prompt(article: dict) -> str:
    article_text = article["text"][:MAX_ARTICLE_TEXT_CHARS]
    return f"""You are summarizing articles for a Principal Architect working at an SSP in the programmatic advertising industry.

Analyze the article below and return a structured Markdown summary.

Focus on:
- What happened
- What problem or workflow challenge is being discussed
- What solution, product, partnership, regulation, or market shift is described
- Companies and industry bodies mentioned
- Named people mentioned, with role or context when available
- Why this matters to an SSP / programmatic advertising architect
- CTV, identity, privacy, auctions, publisher monetization, Prebid, retail media, measurement, and clean room implications when relevant

Formatting requirements:
- "Companies Mentioned" must be a bullet list
- "Key People Mentioned" must be a bullet list
- "Topic Tags" must be a bullet list
- Keep topic tags short, without leading # characters

Return only Markdown with these exact headings:

## Summary

## Problem / Workflow Challenge

## Solution / Key Development

## Companies Mentioned

## Key People Mentioned

## Why This Matters for My Work

## Topic Tags

Article title: {article['title']}
Article URL: {article['url']}
Publication date: {article.get('publication_date') or 'Unknown'}

Article text:
{article_text}
"""


def parse_markdown_sections(markdown: str) -> dict:
    sections = {heading: "" for heading in SECTION_HEADINGS}
    current_heading = None
    buffer: list[str] = []

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_heading is not None:
                sections[current_heading] = "\n".join(buffer).strip()
            current_heading = stripped[3:].strip()
            buffer = []
            continue
        if current_heading is not None:
            buffer.append(line)

    if current_heading is not None:
        sections[current_heading] = "\n".join(buffer).strip()

    return sections


def list_items_from_section(section_text: str) -> list[str]:
    items = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            items.append(stripped[2:].strip())
        elif stripped and not stripped.startswith("#"):
            parts = [part.strip().lstrip("#").strip() for part in stripped.split(",")]
            if len(parts) > 1:
                items.extend([part for part in parts if part])
    return items
