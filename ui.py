"""Presentation helpers: theme CSS and HTML snippets for the Streamlit page.

All text that comes from the letter (via the model) is escaped with e() before it is put
into HTML, and interface texts go through t.h(), so a letter or a translation can never
inject markup or scripts into the page.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

from i18n import Strings
from letter_analyzer import KeyDate, LetterAnalysis, days_until

CSS_FILE = Path(__file__).parent / "assets" / "style.css"
SENDER_ICONS = {
    "government": "🏛️", "tax office": "🧾", "health insurance": "🩺", "insurance": "🛡️",
    "landlord": "🏠", "bank": "🏦", "employer": "💼", "utility": "⚡",
    "debt collector": "📮", "court": "⚖️", "other": "✉️",
}


def e(text: object) -> str:
    return escape(str(text or ""))


def inject_css() -> None:
    st.html(f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>")


def hero(t: Strings) -> None:
    st.html(
        f"""
        <div class="bk-hero">
          <span class="bk-kicker">{t.h("kicker")}</span>
          <div class="bk-title">Briefklar</div>
          <p class="bk-sub">{t.h("sub")}</p>
          <div class="bk-chips">
            <span class="bk-chip c1">{t.h("chip_stored")}</span>
            <span class="bk-chip c2">{t.h("chip_fast")}</span>
            <span class="bk-chip c3">{t.h("chip_glossary")}</span>
          </div>
          <p class="bk-privacy-note">{t.h("privacy_note")}</p>
        </div>
        """
    )


def how_it_works(t: Strings) -> None:
    steps = "".join(
        f'<div class="bk-step"><div class="bk-step-ico">{icon}</div>'
        f'<div class="bk-step-t">{t.h(f"how{i}_t")}</div>'
        f'<div class="bk-step-d">{t.h(f"how{i}_d")}</div></div>'
        for i, icon in enumerate(("📸", "🧠", "✅"), 1)
    )
    st.html(f'<div class="bk-steps">{steps}</div>')


def result_header(a: LetterAnalysis, t: Strings) -> None:
    days = days_until(a.deadline)
    if days is None:
        num, txt, pct = "–", t.h("ring_none"), 0
        date_line = e(a.deadline.description) if a.deadline else t.h("ring_nothing")
    else:
        num = "!" if days < 0 else str(days)
        key = "ring_overdue" if days < 0 else "ring_today" if days == 0 else "ring_day" if days == 1 else "ring_days"
        txt = t.h(key)
        pct = 100 if days <= 0 else max(8, min(100, round((1 - days / 30) * 100)))
        date_line = e(a.deadline.date) + (f" · {t.h('estimated')}" if a.deadline.is_estimated else "")

    icon = SENDER_ICONS.get(a.sender_type, "✉️")
    letter_date = f"<span>📅 {e(a.letter_date)}</span>" if a.letter_date else ""
    st.html(
        f"""
        <div class="bk-result {a.urgency}">
          <div>
            <div class="bk-meta"><span>{icon} {e(a.sender)}</span>{letter_date}</div>
            <div class="bk-subject">{e(a.subject)}</div>
            <span class="bk-urgency {a.urgency}"><span class="bk-dot"></span>{t.h(f"urgency_{a.urgency}")}</span>
            <p class="bk-reason">{e(a.urgency_reason)}</p>
          </div>
          <div class="bk-ring-wrap">
            <div class="bk-ring" style="--p:{pct}">
              <div class="bk-ring-inner"><div class="bk-ring-num">{num}</div><div class="bk-ring-txt">{txt}</div></div>
            </div>
            <div class="bk-ring-date">{date_line}</div>
          </div>
        </div>
        """
    )


def callout(kind: str, icon: str, html_body: str) -> None:
    """kind: warn | danger | info. html_body must already be escaped."""
    st.html(f'<div class="bk-callout {kind}"><span class="ico">{icon}</span><div>{html_body}</div></div>')


def card(label_html: str, text: str) -> None:
    st.html(f'<div class="bk-card"><div class="bk-label">{label_html}</div><p>{e(text)}</p></div>')


def progress(done: int, total: int, t: Strings) -> None:
    pct = round(done / total * 100) if total else 0
    st.html(
        f'<div class="bk-label">{t.h("progress", done=done, total=total)}</div>'
        f'<div class="bk-progress"><div style="width:{pct}%"></div></div>'
    )


def timeline(a: LetterAnalysis, t: Strings) -> None:
    dates = list(a.key_dates)
    # The main deadline always belongs on the timeline, even if the model didn't list it.
    if a.deadline and a.deadline.date and all(d.date != a.deadline.date for d in dates):
        dates.append(KeyDate(date=a.deadline.date, what=a.deadline.description))
    items = []
    for i, d in enumerate(sorted(dates, key=lambda d: d.date)):
        days = days_until(d)
        if days is None:
            cls, status = "", ""
        elif days < 0:
            cls, status = "past", t.h("tl_passed", n=-days) if d.needs_action else t.h("tl_past")
        elif days == 0:
            cls, status = "today", t.h("tl_today")
        else:
            cls, status = "", t.h("tl_in_day") if days == 1 else t.h("tl_in_days", n=days)
        badge = f'<span class="bk-tl-status">{status}</span>' if status else ""
        items.append(
            f'<div class="bk-tl-item {cls}" style="animation-delay:{i * 0.08:.2f}s">'
            f'<div class="bk-tl-date">{e(d.date)}{badge}</div>'
            f'<div class="bk-tl-what">{e(d.what)}</div></div>'
        )
    st.html(f'<div class="bk-card"><div class="bk-timeline">{"".join(items)}</div></div>')


def glossary(a: LetterAnalysis) -> None:
    cards = "".join(
        f'<div class="bk-term" style="animation-delay:{i * 0.06:.2f}s">'
        f'<div class="bk-term-de">{e(g.german)}</div>'
        f'<div class="bk-term-en">{e(g.translation)}</div>'
        f'<div class="bk-term-ex">{e(g.explanation)}</div></div>'
        for i, g in enumerate(a.glossary)
    )
    st.html(f'<div class="bk-glossary">{cards}</div>')


def footer(t: Strings) -> None:
    st.html(f'<div class="bk-foot">{t.h("footer")}</div>')
