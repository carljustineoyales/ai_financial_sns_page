"""Extracts text from a downloaded disclosure PDF and asks an LLM to analyze it."""

import json
import os

from pypdf import PdfReader

import llm

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def _load_prompt(name):
    with open(os.path.join(PROMPTS_DIR, name)) as f:
        return f.read()


def extract_text(pdf_path, max_chars=15000):
    reader = PdfReader(pdf_path)
    pages_text = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n".join(pages_text).strip()
    return full_text[:max_chars]


def analyze(text, company, template_name):
    prompt = _load_prompt("disclosure_analysis.txt").format(
        company=company, template_name=template_name, text=text
    )

    return llm.generate(prompt)


def generate_caption(analysis_text, company, template_name):
    prompt = _load_prompt("facebook_caption.txt").format(
        company=company, template_name=template_name, analysis=analysis_text
    )

    return llm.generate(prompt)


def extract_report_card(text, company, template_name):
    """Asks the LLM to extract only the report-card figures explicitly
    stated in the disclosure text -- each numeric field as a {"stated":,
    "value":} pair, plus REIT-only fields for the 8 PSE REITs (see
    prompts/financial_report_card_extraction.txt for the exact field
    list). Returns a dict with those fields, using None for anything the
    filing didn't disclose. Never computes ratios -- that's
    analysis.ratios's job, done in Python from the "value"s here.
    """
    prompt = _load_prompt("financial_report_card_extraction.txt").format(
        company=company, template_name=template_name, text=text
    )

    response = llm.generate(prompt).strip()
    if response.startswith("```"):
        response = response.strip("`")
        if response.startswith("json"):
            response = response[4:]
        response = response.strip()

    return json.loads(response)


def generate_report_card_caption(symbol, period, figures_text, filed_on):
    prompt = _load_prompt("financial_report_card_caption.txt").format(
        symbol=symbol,
        period=period or "unspecified period",
        figures=figures_text,
        filed_on=filed_on,
    )

    return llm.generate(prompt)
