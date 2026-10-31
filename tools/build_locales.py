"""Generate locales/<code>.json for the languages listed in i18n.LANGUAGES.

Run after changing the English texts in i18n.EN:
    python tools/build_locales.py            # only missing or outdated languages
    python tools/build_locales.py --all      # regenerate every language
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
from google import genai  # noqa: E402

import i18n  # noqa: E402
from letter_analyzer import translate_strings  # noqa: E402


def main() -> None:
    load_dotenv(override=True)
    client = genai.Client()  # reads GEMINI_API_KEY
    i18n.LOCALES_DIR.mkdir(exist_ok=True)
    rebuild_all = "--all" in sys.argv

    for lang in i18n.LANGUAGES:
        if lang.code == "en":
            continue
        path = i18n.LOCALES_DIR / f"{lang.code}.json"
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        missing = {k: v for k, v in i18n.EN.items() if rebuild_all or k not in existing}
        if not missing:
            print(f"{lang.code}: up to date")
            continue
        translated = translate_strings(missing, lang.name, client)
        unchanged = sum(translated[k] == i18n.EN[k] for k in missing)
        merged = {k: {**existing, **translated}[k] for k in i18n.EN}  # keep EN key order
        path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{lang.code}: translated {len(missing)} texts ({unchanged} kept in English)")


if __name__ == "__main__":
    main()
