"""Interface languages.

English texts live here. Common languages have ready-made translations in locales/<code>.json
(generated with tools/build_locales.py). Any other language the user types is translated
live by Gemini once and then cached on the server. These are interface texts only, never
letter content.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

import streamlit as st
from google import genai

from letter_analyzer import translate_strings

LOCALES_DIR = Path(__file__).parent / "locales"
OTHER = "🌍 Other…"


@dataclass(frozen=True)
class Language:
    label: str  # shown in the picker, in the language itself
    name: str  # used in prompts
    code: str = ""  # file name in locales/, empty for typed-in languages

    @property
    def rtl(self) -> bool:
        return any(w in self.name.lower() for w in ("arabic", "persian", "farsi", "urdu", "hebrew", "pashto"))


LANGUAGES = [
    Language("English", "English", "en"),
    Language("Español", "Spanish", "es"),
    Language("Türkçe", "Turkish", "tr"),
    Language("العربية", "Arabic", "ar"),
    Language("Українська", "Ukrainian", "uk"),
    Language("Русский", "Russian", "ru"),
    Language("Polski", "Polish", "pl"),
    Language("Français", "French", "fr"),
    Language("Português", "Portuguese", "pt"),
    Language("Italiano", "Italian", "it"),
    Language("Română", "Romanian", "ro"),
    Language("हिन्दी", "Hindi", "hi"),
    Language("فارسی", "Persian", "fa"),
    Language("Tiếng Việt", "Vietnamese", "vi"),
    Language("中文", "Chinese (Simplified)", "zh"),
    Language("Deutsch (einfach)", "simple German (easy words, short sentences, A2 level)", "de"),
]

EN = {
    "kicker": "📬 Deutsch → your language · letter decoder",
    "sub": "Snap a photo of that scary letter from the Behörde, insurer or landlord. "
    "Get a plain-language summary, your to-do list and the deadline in seconds.",
    "chip_stored": "🔒 Nothing stored",
    "chip_fast": "⚡ About 5 seconds",
    "chip_glossary": "📖 Glossary included",
    "privacy_note": "Letters are sent to Google Gemini (free tier) for analysis. "
    "Please black out your name, address and ID numbers first.",
    "other_prompt": "Type any language",
    "other_placeholder": "e.g. Swahili, Tamil, Kurdish",
    "translating_ui": "Translating the app into {language}…",
    "translating_result": "Translating your result…",
    "data_title": "🛡️ How your data is handled",
    "data_1": "**This app stores nothing.** Uploads are processed in memory and never written "
    "to disk or a database. Results disappear when you close or reload the tab.",
    "data_2": "Your file is sent to Google's Gemini API to generate the explanation.",
    "data_3": "This demo uses Gemini's **free tier**, where Google may use uploads to improve "
    "its products and human reviewers may read them.",
    "data_4": "**Black out your name, address and ID numbers before uploading.**",
    "no_key": "<b>No API key found.</b> Set <code>GEMINI_API_KEY</code> in a <code>.env</code> "
    "file (see <code>.env.example</code>).",
    "upload_label": "Drop your letter here: a photo or PDF. Add several photos for multi-page letters.",
    "btn_decode": "✨ Decode my letter",
    "btn_sample": "🎲 Try a sample letter",
    "status_working": "Decoding your letter…",
    "step_prepare": "📸 Preparing your file",
    "step_read": "🧠 Reading the German and writing your explanation",
    "status_done": "Done! Your letter is decoded",
    "toast_done": "Your letter is decoded",
    "error_generic": "Something went wrong while reading the file: {error}",
    "how1_t": "Upload",
    "how1_d": "A photo or PDF. Several photos for multi-page letters.",
    "how2_t": "AI reads it",
    "how2_d": "Gemini reads the German, stamps and small print.",
    "how3_t": "You act",
    "how3_d": "Summary, to-dos, deadline and the key German words.",
    "urgency_high": "HIGH URGENCY",
    "urgency_medium": "MEDIUM URGENCY",
    "urgency_low": "LOW URGENCY",
    "ring_days": "days left",
    "ring_day": "day left",
    "ring_today": "today",
    "ring_overdue": "overdue",
    "ring_none": "no deadline",
    "ring_nothing": "Nothing to meet",
    "estimated": "estimated",
    "not_letter": "This doesn't look like a letter. The results may not be meaningful.",
    "passed_title": "Some dates in this letter have already passed:",
    "passed_hint": "Check which of the steps still apply.",
    "tab_summary": "✨ Summary",
    "tab_todo": "✅ To-do",
    "tab_dates": "📅 Dates",
    "tab_glossary": "📖 Glossary",
    "tab_details": "🔖 Details",
    "plain_label": "In plain words",
    "ignore_title": "If you ignore it:",
    "no_action": "<b>No action needed.</b> This letter is just for your information.",
    "progress": "{done} of {total} done",
    "all_done": "<b>All done!</b> Keep the letter with your records.",
    "no_dates": "No specific dates are mentioned in this letter.",
    "deadline_label": "Deadline:",
    "german_label": "German:",
    "estimated_note": "This date is <b>estimated</b> from a relative period, so check it.",
    "tl_passed": "passed {n} days ago",
    "tl_past": "past",
    "tl_today": "today",
    "tl_in_days": "in {n} days",
    "tl_in_day": "tomorrow",
    "no_glossary": "No special German terms in this letter.",
    "from_label": "From",
    "refs_label": "Reference numbers · quote these when you reply, pay or call",
    "download": "⬇️ Download summary (.txt)",
    "footer": "AI-generated explanation, not legal advice. For important matters, check with "
    "the sender, a Beratungsstelle, or a lawyer.",
    "rep_subject": "Subject",
    "rep_urgency": "Urgency",
    "rep_references": "References",
    "rep_key_dates": "Key dates",
    "rep_summary": "SUMMARY",
    "rep_todo": "WHAT YOU NEED TO DO",
    "rep_nothing": "Nothing.",
    "rep_ignore": "IF YOU IGNORE IT",
    "rep_glossary": "GLOSSARY",
    "rep_unknown": "unknown",
}

_ALLOWED_TAGS = re.compile(r"&lt;(/?(?:b|i|code))&gt;")


class Strings:
    """t("key", n=3) gives plain text; t.h("key") gives text that is safe to put in HTML."""

    def __init__(self, texts: dict[str, str]):
        self.texts = {**EN, **texts}

    def __call__(self, key: str, **kw) -> str:
        text = self.texts.get(key, EN[key])
        try:
            return text.format(**kw) if kw else text
        except (KeyError, IndexError, ValueError):  # a broken translation: use English
            return EN[key].format(**kw) if kw else EN[key]

    def h(self, key: str, **kw) -> str:
        # Escape everything, then allow back only simple formatting tags.
        return _ALLOWED_TAGS.sub(r"<\1>", escape(self(key, **kw)))


def _load_locale(code: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{code}.json"
    if code == "en" or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False, max_entries=50)
def _live_translation(language: str, _client: genai.Client) -> dict[str, str]:
    # Cached by language name only; the texts are the same for every user.
    return translate_strings(EN, language, _client)


def strings_for(lang: Language, client: genai.Client | None) -> Strings:
    if lang.code:
        return Strings(_load_locale(lang.code))
    if client is None:
        return Strings({})
    return Strings(_live_translation(lang.name, client))


def rtl_css() -> str:
    """Mirror the layout for right-to-left languages."""
    return """<style>
      .stApp { direction: rtl; }
      .bk-timeline { padding-left: 0; padding-right: 26px; }
      .bk-timeline::before { left: auto; right: 8px; }
      .bk-tl-item::before { left: auto; right: -24px; }
      .bk-tl-status { margin-left: 0; margin-right: 8px; }
      .bk-result::before { inset: 0 0 0 auto; }
      .bk-ring-num, .bk-tl-date, code, pre { direction: ltr; unicode-bidi: isolate; }
      .bk-tl-date { text-align: right; }
    </style>"""
