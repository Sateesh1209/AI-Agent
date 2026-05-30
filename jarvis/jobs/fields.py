"""Generic application-form field logic (works on ANY job portal).

This is portal-agnostic: it classifies a field by its visible label and reads
the fields on whatever page the browser is currently on — Workday, Greenhouse,
Lever, a company site, etc. Nothing here is specific to one provider.
"""

from __future__ import annotations

from typing import Any

# Map a profile attribute to the label keywords that identify its field.
_FIELD_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("first_name", ("first name", "firstname", "given name", "legal first")),
    ("last_name", ("last name", "lastname", "surname", "family name", "legal last")),
    ("email", ("email", "e-mail")),
    ("phone", ("phone", "mobile", "telephone", "contact number")),
    ("linkedin", ("linkedin",)),
    ("github", ("github",)),
    ("website", ("website", "portfolio", "personal site")),
    ("location", ("location", "city", "address", "where are you based")),
    ("full_name", ("full name", "your name", "name")),  # generic, checked last
]

_RESUME_KEYWORDS = ("resume", "cv", "résumé", "resumé")


def classify_field(label: str) -> tuple[str, str]:
    """Classify a form field by its label.

    Returns one of:
      ("profile", "<profile_attr>")  -> fill automatically from the profile
      ("resume", "")                 -> attach the tailored resume file
      ("tricky", "")                 -> needs the user (essays, custom questions)
    """
    text = (label or "").strip().lower()
    if not text:
        return ("tricky", "")
    if any(k in text for k in _RESUME_KEYWORDS):
        return ("resume", "")
    for attr, keywords in _FIELD_KEYWORDS:
        if any(k in text for k in keywords):
            return ("profile", attr)
    return ("tricky", "")


def read_form_fields(session) -> list[dict[str, Any]]:
    """Read the visible form fields on the current page (best-effort).

    Includes each field's current ``value`` so the autofiller can skip ones the
    site already populated and only "finish the rest".
    """
    fields: list[dict[str, Any]] = []
    elements = session.page.query_selector_all(
        "input:not([type=hidden]):not([type=submit]):not([type=button]), "
        "textarea, select"
    )
    for el in elements:
        try:
            tag = el.evaluate("e => e.tagName").lower()
            input_type = (el.get_attribute("type") or tag).lower()
            name = el.get_attribute("name") or ""
            el_id = el.get_attribute("id") or ""
            aria = el.get_attribute("aria-label") or ""
            placeholder = el.get_attribute("placeholder") or ""
            label = aria or placeholder or name
            if el_id:
                lab = session.page.query_selector(f"label[for='{el_id}']")
                if lab:
                    label = (lab.inner_text() or label).strip()
            required = bool(el.get_attribute("required")) or "*" in label
            try:
                current = el.input_value() if input_type != "file" else ""
            except Exception:
                current = ""
            selector = f"#{el_id}" if el_id else (f"[name='{name}']" if name else None)
            if not selector:
                continue
            fields.append(
                {
                    "label": label,
                    "selector": selector,
                    "type": input_type,
                    "required": required,
                    "value": current,
                }
            )
        except Exception:
            continue  # skip anything that detaches/errors mid-read
    return fields


def is_empty(field: dict[str, Any]) -> bool:
    """True if the field hasn't been filled yet (so JARVIS should finish it)."""
    if field.get("type") == "file":
        return True  # we can't read file inputs; attempt the resume attach
    return not str(field.get("value", "")).strip()
