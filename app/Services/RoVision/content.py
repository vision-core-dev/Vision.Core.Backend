import math
import re
import bleach

ALLOWED_TAGS = [
    "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u", "s", "sub", "sup",
    "a",
    "ul", "ol", "li",
    "blockquote", "cite",
    "code", "pre",
    "img", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "td", "th",
    "span", "div",
]

ALLOWED_ATTRS = {
    "*": ["class", "id"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height", "loading"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

_WORD_RE = re.compile(r"[\w'\u0400-\u04FF\u2019-]+", re.UNICODE)
_TAG_RE = re.compile(r"<[^>]+>")


def sanitize_html(html: str | None) -> str:
    if not html:
        return ""
    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )
    cleaned = bleach.linkify(
        cleaned,
        callbacks=[lambda attrs, new: {**attrs, (None, "rel"): "nofollow noopener"}],
        skip_tags=["pre", "code"],
    )
    return cleaned


def estimate_reading_time(html: str | None, wpm: int = 200) -> str:
    if not html:
        return "1 хв"
    text = _TAG_RE.sub(" ", html)
    words = _WORD_RE.findall(text)
    count = len(words)
    if count == 0:
        return "1 хв"
    minutes = max(1, math.ceil(count / wpm))
    return f"{minutes} хв"
