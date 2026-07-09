# Codex Implementation Instructions — Local GitHub Repo Article Monitor

## 1. Project Goal

Build a local, file-based article monitoring tool.

The user will create an empty GitHub repository, clone it locally, and ask Codex to implement this project inside that repo.

The tool should:

1. Read a YAML config containing websites and sections to monitor.
2. Visit configured website sections.
3. Discover article URLs.
4. Skip URLs already processed in local state files.
5. Fetch and extract article content.
6. Summarize each new article using an LLM.
7. Save each summary as a Markdown file under website/section-specific folders.
8. Generate a daily digest Markdown file.
9. Update local JSON state files.
10. Leave all generated changes in the repo for the user to review, commit, and push manually.

This is a v1 local-only implementation.

Do not implement GitHub Actions, scheduled cloud runs, database storage, web UI, Slack, or email notifications in v1.

---

## 2. Core Design Principles

Follow these principles strictly:

- No database.
- No SQLite.
- No cloud storage.
- No GitHub Actions in v1.
- No automatic git commit or push in v1.
- Config should be stored in YAML files.
- State should be stored in JSON files.
- Outputs should be stored as Markdown files.
- Logs should be stored as plain text files.
- The local GitHub repo is the durable storage and version history.
- The script should be safe to run multiple times without creating duplicates.
- The user should manually review, commit, and push generated files.

---

## 3. Expected Repository Structure

Create the following structure:

```text
article-monitor/
  README.md
  .gitignore
  .env.example
  requirements.txt

  config/
    websites.yaml

  scripts/
    run.py
    config_loader.py
    discover_articles.py
    extract_article.py
    summarize_article.py
    file_store.py
    state_store.py
    digest_writer.py
    llm_client.py
    utils.py

  state/
    visited_urls.json
    article_counters.json
    run_history.json

  outputs/
    .gitkeep

  digests/
    daily/
      .gitkeep

  logs/
    .gitkeep
```

If any folder does not exist, the script should create it automatically.

---

## 4. V1 Workflow

The user should be able to run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/run.py
```

The script should then:

1. Load environment variables.
2. Load `config/websites.yaml`.
3. Load or initialize JSON state files.
4. Iterate through configured websites and sections.
5. Discover article links from each section page.
6. Normalize URLs.
7. Filter out already visited URLs.
8. Limit articles using `max_articles_per_run`.
9. Fetch each article.
10. Extract title, publication date, author if available, article text, and image URLs.
11. Summarize the article using the configured LLM provider.
12. Save the article summary as Markdown.
13. Update visited URL state.
14. Update article counters.
15. Generate or update a daily digest file.
16. Append run details to run history.
17. Write logs.
18. Exit without committing anything to git.

---

## 5. Configuration File

Create `config/websites.yaml` with this example content:

```yaml
settings:
  default_max_articles_per_run: 5
  request_timeout_seconds: 20
  user_agent: "Mozilla/5.0 article-monitor-bot/1.0"
  llm_provider: "openai"
  llm_model: "gpt-4o-mini"
  output_timezone: "America/Chicago"

websites:
  - name: "AdExchanger"
    key: "adexchanger"
    base_url: "https://www.adexchanger.com"
    output_folder: "outputs/adexchanger"
    sections:
      - name: "Streaming"
        key: "streaming"
        url: "https://www.adexchanger.com/streaming/"
        max_articles_per_run: 5

      - name: "Programmatic"
        key: "programmatic"
        url: "https://www.adexchanger.com/programmatic/"
        max_articles_per_run: 5

  - name: "Digiday"
    key: "digiday"
    base_url: "https://digiday.com"
    output_folder: "outputs/digiday"
    sections:
      - name: "Media Buying"
        key: "media-buying"
        url: "https://digiday.com/media-buying/"
        max_articles_per_run: 5
```

The script should validate this config and fail clearly if required fields are missing.

Required fields:

- `websites[].name`
- `websites[].key`
- `websites[].base_url`
- `websites[].output_folder`
- `websites[].sections[].name`
- `websites[].sections[].key`
- `websites[].sections[].url`

---

## 6. Environment File

Create `.env.example`:

```bash
OPENAI_API_KEY=
```

The real `.env` file must not be committed.

`.gitignore` should include:

```gitignore
.env
.venv/
__pycache__/
*.pyc
*.tmp
.DS_Store
```

---

## 7. State Files

### 7.1 `state/visited_urls.json`

Purpose: prevent duplicate processing.

Initial content:

```json
{}
```

Recommended structure after runs:

```json
{
  "adexchanger": {
    "streaming": [
      {
        "url": "https://www.adexchanger.com/example/article/",
        "title": "Example Article",
        "processed_at": "2026-07-08T09:15:00-05:00",
        "output_file": "outputs/adexchanger/streaming/0001_example-article.md"
      }
    ]
  }
}
```

Use objects rather than raw URL strings so the state file is useful for auditing.

### 7.2 `state/article_counters.json`

Purpose: maintain incrementing article numbers per website and section.

Initial content:

```json
{}
```

Example after processing:

```json
{
  "adexchanger": {
    "streaming": 7,
    "programmatic": 3
  },
  "digiday": {
    "media-buying": 4
  }
}
```

### 7.3 `state/run_history.json`

Purpose: track each execution.

Initial content:

```json
[]
```

Example entry:

```json
{
  "run_id": "2026-07-08T09-15-00-05-00",
  "started_at": "2026-07-08T09:15:00-05:00",
  "completed_at": "2026-07-08T09:18:44-05:00",
  "websites_processed": 2,
  "sections_processed": 3,
  "new_articles_found": 8,
  "articles_processed": 8,
  "articles_failed": 0,
  "errors": []
}
```

---

## 8. Article Discovery

Implement `scripts/discover_articles.py`.

The discovery function should:

1. Fetch the configured section URL.
2. Parse HTML with BeautifulSoup.
3. Extract candidate article links from `<a href="...">` tags.
4. Convert relative URLs to absolute URLs.
5. Remove query strings and fragments unless needed.
6. Remove duplicates while preserving order.
7. Keep only URLs within the configured website base domain.
8. Filter obvious non-article URLs.

Filter out URLs containing patterns like:

```text
/tag/
/author/
/category/
/page/
/about
/contact
/privacy
/terms
/newsletter
/events
#
mailto:
javascript:
```

Do not overfit to one website. Keep generic discovery logic in v1.

Optional but recommended: if a section has an RSS feed in the future config, prefer RSS over HTML scraping. Do not make RSS mandatory in v1.

---

## 9. Article Extraction

Implement `scripts/extract_article.py`.

Use `trafilatura` if possible because it handles article extraction better than raw BeautifulSoup.

Extraction should return this structure:

```python
{
    "title": "...",
    "url": "...",
    "publication_date": "...",
    "author": "...",
    "text": "...",
    "image_urls": ["..."],
    "raw_metadata": {}
}
```

Extraction requirements:

- Title should come from article metadata, Open Graph title, `<title>`, or first `<h1>`.
- Publication date should come from article metadata, JSON-LD, Open Graph, `<time>`, or meta tags.
- Author is optional.
- Text is required. If text cannot be extracted, mark the article as failed and log the error.
- Image URLs should be collected from Open Graph image, article images, and absolute image URLs found on the page.

If article text is very short, treat it as extraction failure unless the article itself is actually short.

Use a reasonable minimum threshold, for example 500 characters.

---

## 10. LLM Summarization

Implement `scripts/llm_client.py` and `scripts/summarize_article.py`.

Use OpenAI by default.

Environment variable:

```bash
OPENAI_API_KEY=
```

Model should come from config:

```yaml
settings:
  llm_model: "gpt-4o-mini"
```

The summarizer should produce structured content with these sections:

1. Summary
2. Problem / Workflow Challenge
3. Solution / Key Development
4. Companies Mentioned
5. Key People Mentioned
6. Why This Matters for My Work
7. Topic Tags

The "Why This Matters for My Work" section should be written from the perspective of a principal architect working in an SSP/programmatic advertising company, especially around CTV, identity, privacy, auctions, publisher monetization, Prebid, clean rooms, retail media, and ad tech architecture.

Prompt template:

```text
You are summarizing articles for a Principal Architect working at an SSP in the programmatic advertising industry.

Analyze the article below and return a structured Markdown summary.

Focus on:
- What happened
- What problem or workflow challenge is being discussed
- What solution, product, partnership, regulation, or market shift is described
- Companies and industry bodies mentioned
- Why this matters to an SSP / programmatic advertising architect
- CTV, identity, privacy, auctions, publisher monetization, Prebid, retail media, measurement, and clean room implications when relevant

Return only Markdown with these exact headings:

## Summary

## Problem / Workflow Challenge

## Solution / Key Development

## Companies Mentioned

## Key People Mentioned

## Why This Matters for My Work

## Topic Tags

Article title: {title}
Article URL: {url}
Publication date: {publication_date}

Article text:
{text}
```

Companies should be returned as a bullet list. Topic tags should also be returned as a bullet list.
Key people should be returned as a bullet list of the most relevant named individuals mentioned in the article, with short role/context when available so they are useful for follow-up on LinkedIn.

---

## 11. Markdown Output Format

Implement `scripts/file_store.py`.

Each article should be saved as:

```text
outputs/{website_key}/{section_key}/{counter}_{slugified-title}.md
```

Example:

```text
outputs/adexchanger/streaming/0001_programmatic-pause-ads.md
```

Markdown file format:

```markdown
# Article Title

**Source:** AdExchanger  
**Section:** Streaming  
**URL:** https://example.com/article  
**Publication Date:** 2026-07-08  
**Author:** Author Name  
**Processed Date:** 2026-07-08T09:15:00-05:00  

---

## Summary

...

## Problem / Workflow Challenge

...

## Solution / Key Development

...

## Companies Mentioned

- Company A
- Company B

## Key People Mentioned

- Jane Smith, CEO, Example Co.
- John Doe, Head of Product, Example Co.

## Why This Matters for My Work

...

## Topic Tags

- CTV
- Programmatic
- SSP

## Image Links

- https://example.com/image1.jpg
```

Use slugified titles:

- Lowercase
- Replace spaces with hyphens
- Remove special characters
- Limit slug length to around 80 characters

Use zero-padded counters with four digits:

```text
0001
0002
0003
```

---

## 12. Daily Digest

Implement `scripts/digest_writer.py`.

Create one file per run date:

```text
digests/daily/YYYY-MM-DD.md
```

If the file already exists, append a new run section or update it cleanly.

Digest format:

```markdown
# Daily Article Digest — 2026-07-08

## Run Summary

- Run ID: 2026-07-08T09-15-00-05-00
- New articles processed: 8
- Failed articles: 0

## Articles Processed

### AdExchanger / Streaming

1. [Article Title](../../outputs/adexchanger/streaming/0001_article-title.md)
   - URL: https://example.com/article
   - Publication Date: 2026-07-08
   - Key People: Jane Smith, John Doe
   - Topic Tags: CTV, Programmatic, SSP

## Key Themes

- Theme 1
- Theme 2
- Theme 3

## Companies Mentioned Today

- Company A
- Company B
- Company C
```

For v1, the digest can be created from article metadata and summaries. It does not need a second LLM pass, but a second LLM pass to generate cross-article themes is acceptable if implemented cleanly.

---

## 13. Logging

Create daily log files:

```text
logs/YYYY-MM-DD.log
```

Log:

- Run start
- Config loaded
- Website/section being processed
- Number of article links discovered
- Number skipped as already visited
- Number selected for processing
- Article extraction success/failure
- Summary success/failure
- Files written
- State updated
- Run completed

Use Python logging module.

---

## 14. Error Handling

The script should continue processing other articles if one article fails.

Failures should be captured in:

- Logs
- Run history
- Console output

Common failures to handle:

- HTTP timeout
- HTTP non-200 response
- Invalid HTML
- Article text extraction failed
- LLM API error
- Invalid config
- JSON state file missing
- JSON state file corrupt
- File write error

If a state file is missing, initialize it.

If a state file is corrupt, stop with a clear error. Do not overwrite corrupt state silently.

---

## 15. Atomic State Writes

When writing JSON state files, write atomically:

1. Write to a temporary file.
2. Flush and close it.
3. Replace the original file.

Example:

```text
state/visited_urls.json.tmp -> state/visited_urls.json
```

This prevents corrupted state if the process crashes midway.

---

## 16. Idempotency

The script must be idempotent.

If the user runs it twice on the same day, the second run should not duplicate already processed articles.

Deduplication should be based on normalized canonical URL.

Before processing an article, check whether its normalized URL already exists in `state/visited_urls.json` for that website/section or globally.

Also keep a global in-memory set of visited URLs during a run so the same URL discovered in two sections is not processed twice.

---

## 17. CLI Behavior

`scripts/run.py` should be executable as:

```bash
python scripts/run.py
```

Optional CLI flags:

```bash
python scripts/run.py --config config/websites.yaml
python scripts/run.py --dry-run
python scripts/run.py --website adexchanger
python scripts/run.py --section streaming
python scripts/run.py --max-articles 3
```

V1 must support at least:

```bash
python scripts/run.py
python scripts/run.py --dry-run
```

Dry-run behavior:

- Load config.
- Discover articles.
- Show what would be processed.
- Do not call LLM.
- Do not write outputs.
- Do not update state.

---

## 18. Dependencies

Use Python 3.11 or newer.

Suggested `requirements.txt`:

```text
beautifulsoup4>=4.12.0
feedparser>=6.0.0
lxml>=5.0.0
openai>=1.0.0
python-dotenv>=1.0.0
PyYAML>=6.0.0
requests>=2.31.0
trafilatura>=1.8.0
python-dateutil>=2.9.0
```

Do not add heavy frameworks unless necessary.

---

## 19. README Requirements

Create a clear `README.md` with:

1. Project overview.
2. V1 scope.
3. What is intentionally not included.
4. Setup instructions.
5. Config instructions.
6. How to run.
7. Dry-run usage.
8. How state files work.
9. How outputs are organized.
10. Manual git workflow.
11. Troubleshooting.

Manual git workflow section:

```bash
git pull
python scripts/run.py
git status
git diff
git add outputs/ digests/ state/ logs/
git commit -m "Add article summaries for YYYY-MM-DD"
git push
```

Be explicit that the script does not commit or push automatically.

---

## 20. Implementation Order

Implement in this order:

1. Create repo structure.
2. Add `.gitignore`, `.env.example`, `requirements.txt`.
3. Add config sample.
4. Implement config loader and validation.
5. Implement state store with atomic JSON writes.
6. Implement URL normalization and slug utilities.
7. Implement article discovery.
8. Implement article extraction.
9. Implement LLM client.
10. Implement summarizer.
11. Implement Markdown file writer.
12. Implement digest writer.
13. Implement main runner.
14. Add dry-run mode.
15. Add logging.
16. Update README.
17. Run a dry-run test.
18. Run a real test with max 1 article.

---

## 21. Acceptance Criteria

The implementation is complete when:

- `python scripts/run.py --dry-run` works without requiring an OpenAI API key.
- `python scripts/run.py` works when `.env` contains `OPENAI_API_KEY`.
- Missing folders are created automatically.
- Missing state files are initialized automatically.
- New article summaries are saved under `outputs/{website}/{section}/`.
- Daily digest is created under `digests/daily/`.
- `visited_urls.json` is updated after successful processing.
- `article_counters.json` increments correctly.
- `run_history.json` receives a new run entry.
- Re-running the script does not duplicate already processed URLs.
- Failures for individual articles do not stop the whole run.
- No database is used.
- No GitHub Actions are created.
- No automatic git commit or push is implemented.
- README clearly explains local manual workflow.

---

## 22. Important Non-Goals for V1

Do not implement these in v1:

- GitHub Actions
- Cron scheduling
- Auto git commit
- Auto git push
- Web dashboard
- Search UI
- Slack notification
- Email notification
- Database
- SQLite
- Docker deployment
- Multi-user support
- Browser extension
- Complex website-specific scrapers unless absolutely required

Keep v1 simple, local, and file-based.

---

## 23. Good Console Output Example

When the user runs the script, console output should look like this:

```text
Article Monitor started: 2026-07-08T09:15:00-05:00
Loaded config: config/websites.yaml
Loaded state files from state/

Processing AdExchanger / Streaming
Discovered 18 candidate article URLs
Skipped 12 already visited URLs
Selected 5 new articles

[1/5] Extracting: Article title here
Saved: outputs/adexchanger/streaming/0001_article-title-here.md

[2/5] Extracting: Another article title
Saved: outputs/adexchanger/streaming/0002_another-article-title.md

Daily digest updated: digests/daily/2026-07-08.md
State updated successfully
Run completed: 5 articles processed, 0 failed

Review changes with:
  git status
  git diff
```

---

## 24. Keep Code Simple and Maintainable

Prefer readable code over clever code.

Use functions with clear responsibilities.

Avoid putting all logic in `run.py`.

Keep website-specific hacks isolated so the generic pipeline remains clean.

Include comments where behavior may not be obvious.
