from pathlib import Path

import yaml


REQUIRED_WEBSITE_FIELDS = ("name", "key", "base_url", "output_folder", "sections")
REQUIRED_SECTION_FIELDS = ("name", "key", "url")


def load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    settings = config.get("settings")
    websites = config.get("websites")

    if not isinstance(settings, dict):
        raise ValueError("Config is missing 'settings' or it is not a mapping.")
    if not isinstance(websites, list) or not websites:
        raise ValueError("Config must define at least one website in 'websites'.")

    for website in websites:
        if not isinstance(website, dict):
            raise ValueError("Each website entry must be a mapping.")
        for field in REQUIRED_WEBSITE_FIELDS:
            if not website.get(field):
                raise ValueError(f"Website is missing required field '{field}'.")

        sections = website.get("sections")
        if not isinstance(sections, list) or not sections:
            raise ValueError(f"Website '{website.get('key', '<unknown>')}' must define at least one section.")

        for section in sections:
            if not isinstance(section, dict):
                raise ValueError("Each section entry must be a mapping.")
            for field in REQUIRED_SECTION_FIELDS:
                if not section.get(field):
                    raise ValueError(
                        f"Section in website '{website['key']}' is missing required field '{field}'."
                    )


def filter_config(config: dict, website_key: str | None, section_key: str | None) -> dict:
    filtered = {"settings": dict(config["settings"]), "websites": []}

    for website in config["websites"]:
        if website_key and website["key"] != website_key:
            continue

        website_copy = dict(website)
        sections = []
        for section in website["sections"]:
            if section_key and section["key"] != section_key:
                continue
            sections.append(dict(section))

        if not sections:
            continue

        website_copy["sections"] = sections
        filtered["websites"].append(website_copy)

    if not filtered["websites"]:
        details = []
        if website_key:
            details.append(f"website={website_key}")
        if section_key:
            details.append(f"section={section_key}")
        suffix = ", ".join(details) if details else "provided filters"
        raise ValueError(f"No websites/sections matched the {suffix}.")

    return filtered
