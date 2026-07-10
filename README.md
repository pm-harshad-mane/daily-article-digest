# Daily Article Digest

Local, file-based article monitoring for ad tech and CTV news sources.

V1 monitors configured website sections, discovers new article URLs, extracts article text, summarizes each article with an LLM, stores the summary as Markdown, and builds a daily digest in the repo. The repo is the durable store. You review the generated changes and commit them manually.

## V1 Scope

- YAML config for websites and sections
- JSON state for visited URLs, counters, and run history
- Markdown output for article summaries and daily digests
- Plain text log files
- Idempotent reruns based on normalized URLs
- Dry-run mode that does not require an OpenAI API key

## Not Included In V1

- GitHub Actions
- Cron or background scheduling
- Database or SQLite
- Slack or email delivery
- Web UI or dashboard
- Automatic git commit or push
- Docker deployment

## Repository Layout

```text
config/
  websites.yaml
scripts/
  run.py
  config_loader.py
  discover_articles.py
  digest_writer.py
  extract_article.py
  file_store.py
  llm_client.py
  state_store.py
  summarize_article.py
  utils.py
state/
  visited_urls.json
  article_counters.json
  run_history.json
outputs/
digests/daily/
logs/
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env` before running a real summarization pass.

Optional override:

- `OPENAI_MODEL` overrides `settings.llm_model` from `config/websites.yaml`

## Config

The default config lives at `config/websites.yaml`.

Current default target:

- `https://www.adexchanger.com/ctv-roundup/`
- `https://www.adexchanger.com/ctv/`

Each website defines:

- `name`
- `key`
- `base_url`
- `output_folder`
- `sections[]`

Each section defines:

- `name`
- `key`
- `url`
- optional `max_articles_per_run`

## Running

Normal run:

```bash
python scripts/run.py
```

Dry run:

```bash
python scripts/run.py --dry-run
```

Useful flags:

```bash
python scripts/run.py --config config/websites.yaml
python scripts/run.py --website adexchanger
python scripts/run.py --section ctv
python scripts/run.py --max-articles 1
```

## How State Works

`state/visited_urls.json`

- Tracks successfully processed article URLs
- Stores URL, title, processed timestamp, and output file

`state/article_counters.json`

- Stores the next zero-padded article number per website/section

`state/run_history.json`

- Stores a summary entry for each execution

State writes are atomic. Missing state files are initialized automatically. Corrupt state files stop the run with a clear error instead of being overwritten.
Log files under `logs/` are local-only and are not meant to be committed.

## Output Layout

Article summaries are stored at:

```text
outputs/{website_key}/{section_key}/{counter}_{slugified-title}.md
```

Daily digest files are stored at:

```text
digests/daily/YYYY-MM-DD.md
```

Each article summary includes:

- source metadata
- structured summary sections
- companies mentioned
- key people mentioned
- topic tags
- image links

## Manual Git Workflow

The script never commits or pushes changes.

```bash
git pull
python scripts/run.py
git status
git diff
git add outputs/ digests/ state/
git commit -m "Add article summaries for YYYY-MM-DD"
git push
```

## Troubleshooting

If `--dry-run` fails:

- verify Python 3.11+ is installed
- verify dependencies from `requirements.txt` are installed
- inspect `logs/YYYY-MM-DD.log`

If a real run fails before summarization:

- verify `OPENAI_API_KEY` is set in `.env`
- verify the target site is reachable from your machine
- verify the state files contain valid JSON

If articles are skipped unexpectedly:

- check `state/visited_urls.json`
- rerun with a narrower `--website` or `--section` filter
- inspect the normalized URLs in the log output
