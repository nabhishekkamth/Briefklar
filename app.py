"""Briefklar - understand German official letters in your own language.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import os
import re
from html import escape
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai

import i18n
import ui
from i18n import Language, Strings
from letter_analyzer import (
    SUPPORTED_IMAGE_TYPES,
    AnalysisError,
    LetterAnalysis,
    analyze_letter,
    build_content,
    passed_dates,
    translate_analysis,
)

load_dotenv(override=True)  # a key in .env wins over one set in the system environment
SAMPLE_LETTER = Path(__file__).parent / "samples" / "sample_letter.txt"
# A typed-in language goes into a prompt, so only allow what a language name looks like.
LANGUAGE_NAME = re.compile(r"^[^\W\d_][\w\s()\-,.']{1,39}$")

st.set_page_config(page_title="Briefklar – German Letter Explainer", page_icon="📬", layout="centered")
ui.inject_css()


def get_client() -> genai.Client | None:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        try:
            key = st.secrets["GEMINI_API_KEY"]
        except Exception:
            key = None
    return genai.Client(api_key=key) if key else None


def pick_language() -> Language:
    """Language picker at the top right. 'Other…' lets the user type any language."""
    _, right = st.columns([3, 2])
    with right:
        labels = [lang.label for lang in i18n.LANGUAGES] + [i18n.OTHER]
        choice = st.selectbox("🌐", labels, key="lang_choice", label_visibility="collapsed")
        if choice != i18n.OTHER:
            return i18n.LANGUAGES[labels.index(choice)]
        typed = st.text_input(
            "🌐", key="lang_other", placeholder="Swahili, Tamil, Kurdish …", label_visibility="collapsed"
        ).strip()
    if typed and LANGUAGE_NAME.match(typed):
        return Language(typed, typed)
    return i18n.LANGUAGES[0]


def to_text_report(a: LetterAnalysis, t: Strings) -> str:
    """Plain-text version of the result for the download button (generated in memory)."""
    lines = [
        f"{t('from_label')}: {a.sender}",
        f"{t('rep_subject')}: {a.subject}",
        f"{t('rep_urgency')}: {t(f'urgency_{a.urgency}')} - {a.urgency_reason}",
    ]
    if a.deadline:
        lines.append(f"{t('deadline_label')} {a.deadline.date or t('rep_unknown')} - {a.deadline.description}")
    if a.reference_numbers:
        lines.append(f"{t('rep_references')}: " + "; ".join(a.reference_numbers))
    if a.key_dates:
        lines.append(f"{t('rep_key_dates')}: " + "; ".join(f"{d.date} {d.what}" for d in a.key_dates))
    lines += ["", t("rep_summary"), a.summary, "", t("rep_todo")]
    lines += [f"{i}. {x.step} - {x.how}" for i, x in enumerate(a.actions, 1)] or [t("rep_nothing")]
    if a.consequences:
        lines += ["", t("rep_ignore"), a.consequences]
    lines += ["", t("rep_glossary")] + [f"{g.german} = {g.translation}: {g.explanation}" for g in a.glossary]
    return "\n".join(lines)


@st.fragment
def todo_list(a: LetterAnalysis, run: int, t: Strings) -> None:
    """A fragment: ticking a box reruns only this list, not the whole page."""
    keys = [f"chk_{run}_{i}" for i in range(len(a.actions))]  # same keys in every language
    done = sum(bool(st.session_state.get(k)) for k in keys)
    ui.progress(done, len(keys), t)
    for i, (action, key) in enumerate(zip(a.actions, keys), 1):
        with st.container(key=f"todo_{run}_{i}"):
            st.checkbox(f"**{i} · {action.step}**  \n{action.how}", key=key)
    if done == len(keys):
        ui.callout("info", "🎉", t.h("all_done"))


def render_result(a: LetterAnalysis, run: int, t: Strings) -> None:
    ui.result_header(a, t)

    if not a.is_letter:
        ui.callout("warn", "🤔", t.h("not_letter"))
    if past := passed_dates(a):
        listed = "; ".join(f"{escape(d.what)} ({escape(d.date)})" for d in past)
        ui.callout("warn", "⏰", f"<b>{t.h('passed_title')}</b> {listed}. {t.h('passed_hint')}")

    tabs = st.tabs([
        t("tab_summary"),
        f"{t('tab_todo')} · {len(a.actions)}",
        t("tab_dates"),
        f"{t('tab_glossary')} · {len(a.glossary)}",
        t("tab_details"),
    ], key=f"tabs_{run}")  # a key keeps the selected tab when the page reruns

    with tabs[0]:
        ui.card(t.h("plain_label"), a.summary)
        if a.consequences:
            ui.callout("danger", "⚠️", f"<b>{t.h('ignore_title')}</b> {escape(a.consequences)}")

    with tabs[1]:
        if a.actions:
            todo_list(a, run, t)
        else:
            ui.callout("info", "🎉", t.h("no_action"))

    with tabs[2]:
        if a.key_dates or (a.deadline and a.deadline.date):
            ui.timeline(a, t)
        else:
            ui.callout("info", "📅", t.h("no_dates"))
        if a.deadline:
            note = f" {t.h('estimated_note')}" if a.deadline.is_estimated else ""
            ui.callout(
                "info", "🗣️",
                f"<b>{t.h('deadline_label')}</b> {escape(a.deadline.description)}<br>"
                f"<i>{t.h('german_label')} „{escape(a.deadline.german_wording)}“</i>{note}",
            )

    with tabs[3]:
        if a.glossary:
            ui.glossary(a)
        else:
            ui.callout("info", "📖", t.h("no_glossary"))

    with tabs[4]:
        ui.card(t.h("from_label"), a.sender)
        if a.reference_numbers:
            st.html(f'<div class="bk-label" style="margin-top:1rem">{t.h("refs_label")}</div>')
            for ref in a.reference_numbers:
                st.code(ref, language=None)
        st.download_button(
            t("download"),
            to_text_report(a, t),
            file_name="letter_summary.txt",
            mime="text/plain",
            width="stretch",
        )

    ui.footer(t)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

client = get_client()
lang = pick_language()
if lang.rtl:
    st.html(i18n.rtl_css())

try:
    if lang.code:
        t = i18n.strings_for(lang, client)
    else:
        with st.spinner(i18n.EN["translating_ui"].format(language=lang.name)):
            t = i18n.strings_for(lang, client)
except AnalysisError as err:
    t = Strings({})
    ui.callout("warn", "🌐", escape(str(err)))

ui.hero(t)

with st.expander(t("data_title")):
    st.markdown("\n".join(f"- {t(f'data_{i}')}" for i in range(1, 5)))

if client is None:
    ui.callout("danger", "🔑", t.h("no_key"))
    st.stop()

uploads = st.file_uploader(
    t("upload_label"),
    type=["pdf", *sorted(SUPPORTED_IMAGE_TYPES)],
    accept_multiple_files=True,
    key="uploads",
)

if uploads:
    images = [u for u in uploads if not u.name.lower().endswith(".pdf")]
    if images:
        st.image([u.getvalue() for u in images], width=110)

col_a, col_b = st.columns(2)
explain = col_a.button(t("btn_decode"), type="primary", disabled=not uploads, width="stretch", key="btn_decode")
sample = col_b.button(t("btn_sample"), width="stretch", key="btn_sample")

if explain or sample:
    with st.status(t("status_working"), expanded=True) as status:
        try:
            st.write(t("step_prepare"))
            if sample:
                content = [f"<letter>\n{SAMPLE_LETTER.read_text(encoding='utf-8')}\n</letter>"]
            else:
                content = build_content([(u.name, u.getvalue()) for u in uploads])
            st.write(t("step_read"))
            result = analyze_letter(content, client, lang.name)
            # One result per language; switching language translates the original.
            st.session_state.results = {lang.name: result}
            st.session_state.original_lang = lang.name
            st.session_state.run = st.session_state.get("run", 0) + 1
            status.update(label=t("status_done"), state="complete", expanded=False)
            st.toast(t("toast_done"), icon="🎉")
        except (AnalysisError, ValueError) as err:
            st.session_state.pop("results", None)
            status.update(label=str(err), state="error", expanded=False)
        except Exception as err:  # e.g. a corrupt image
            st.session_state.pop("results", None)
            status.update(label=t("error_generic", error=err), state="error", expanded=False)

results = st.session_state.get("results")
if results:
    if lang.name not in results:
        try:
            with st.spinner(t("translating_result")):
                original = results[st.session_state.original_lang]
                results[lang.name] = translate_analysis(original, lang.name, client)
        except AnalysisError as err:
            ui.callout("warn", "🌐", escape(str(err)))
    shown = results.get(lang.name) or results[st.session_state.original_lang]
    render_result(shown, st.session_state.get("run", 0), t)
else:
    ui.how_it_works(t)
