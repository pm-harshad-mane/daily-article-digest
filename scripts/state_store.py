import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from utils import ensure_directory


class StateStore:
    def __init__(self, root: str = "state", initialize_missing: bool = True) -> None:
        self.root = Path(root)
        self.initialize_missing = initialize_missing
        if self.initialize_missing:
            ensure_directory(self.root)
        self.visited_path = self.root / "visited_urls.json"
        self.counters_path = self.root / "article_counters.json"
        self.run_history_path = self.root / "run_history.json"

        self.visited_urls = self._load_json(self.visited_path, {})
        self.article_counters = self._load_json(self.counters_path, {})
        self.run_history = self._load_json(self.run_history_path, [])

    def _load_json(self, path: Path, default: dict | list) -> dict | list:
        if not path.exists():
            if self.initialize_missing:
                self._atomic_write_json(path, default)
            return default

        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"State file is corrupt and must be fixed manually: {path}") from exc

    def _atomic_write_json(self, path: Path, payload: dict | list) -> None:
        ensure_directory(path.parent)
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            temp_path = Path(handle.name)
        temp_path.replace(path)

    def all_visited_urls(self) -> set[str]:
        urls = set()
        for website_sections in self.visited_urls.values():
            for section_entries in website_sections.values():
                for entry in section_entries:
                    url = entry.get("url")
                    if url:
                        urls.add(url)
        return urls

    def was_visited(self, website_key: str, section_key: str, normalized_url: str) -> bool:
        if normalized_url in self.all_visited_urls():
            return True
        return any(
            item.get("url") == normalized_url
            for item in self.visited_urls.get(website_key, {}).get(section_key, [])
        )

    def mark_visited(
        self,
        website_key: str,
        section_key: str,
        normalized_url: str,
        title: str,
        processed_at: str,
        output_file: str,
    ) -> None:
        website_state = self.visited_urls.setdefault(website_key, {})
        section_state = website_state.setdefault(section_key, [])
        section_state.append(
            {
                "url": normalized_url,
                "title": title,
                "processed_at": processed_at,
                "output_file": output_file,
            }
        )
        self._atomic_write_json(self.visited_path, self.visited_urls)

    def peek_next_counter(self, website_key: str, section_key: str) -> int:
        website_counters = self.article_counters.setdefault(website_key, {})
        return website_counters.get(section_key, 0) + 1

    def commit_counter(self, website_key: str, section_key: str, counter: int) -> None:
        website_counters = self.article_counters.setdefault(website_key, {})
        website_counters[section_key] = counter
        self._atomic_write_json(self.counters_path, self.article_counters)

    def append_run_history(self, entry: dict) -> None:
        self.run_history.append(entry)
        self._atomic_write_json(self.run_history_path, self.run_history)
