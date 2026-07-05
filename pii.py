import re

PATTERNS = {
    "EMAIL": re.compile(r"[\w\.-]+@[\w\.-]+\.\w+"),
    "PHONE": re.compile(r"\b\d{10}\b"),
    "CARD": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
}


def redact(text: str) -> str:
    """Scan text for common PII patterns and replace with redaction labels.

    Detects:
      - Email addresses (e.g. user@example.com → [REDACTED_EMAIL])
      - 10-digit phone numbers (e.g. 9876543210 → [REDACTED_PHONE])
      - 16-digit card numbers (e.g. 4111-1111-1111-1111 → [REDACTED_CARD])

    Tradeoff: regex is fast and fully transparent, but won't catch
    names, addresses, or non-standard formats. A production system
    would layer in NLP-based NER for higher recall.
    """
    for label, pattern in PATTERNS.items():
        text = pattern.sub(f"[REDACTED_{label}]", text)
    return text
