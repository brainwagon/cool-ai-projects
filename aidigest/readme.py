"""README helpers: pick a preview image and make a compact text excerpt."""

import re
from urllib.parse import urljoin

MD_IMG = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)")
HTML_IMG = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)", re.I)
IMAGE_EXT = re.compile(r"\.(png|jpe?g|gif|webp)(\?|#|$)", re.I)
SKIP = ("badge", "shields.io", "badgen", "star-history", "contrib.rocks",
        "sponsor", "buymeacoffee", "ko-fi", "discord", "twitter", "x.com",
        "visitor", "hits.", "codecov", "travis-ci", "/actions/workflows/",
        "readme-typing", "logo", "icon", "avatar")


def preview_image(text, full_name, branch):
    """First README image that looks like a screenshot or demo."""
    found = sorted([(m.start(), m.group(1)) for m in MD_IMG.finditer(text)]
                   + [(m.start(), m.group(1)) for m in HTML_IMG.finditer(text)])
    base = f"https://raw.githubusercontent.com/{full_name}/{branch}/"
    for _, src in found:
        low = src.lower()
        if any(s in low for s in SKIP) or low.endswith(".svg"):
            continue
        url = urljoin(base, src)
        # github.com/<o>/<r>/blob/<b>/x.png -> raw form
        url = re.sub(r"^https://github\.com/([^/]+/[^/]+)/blob/",
                     r"https://raw.githubusercontent.com/\1/", url)
        if not url.startswith("https://"):
            continue
        if IMAGE_EXT.search(url) or "/user-attachments/assets/" in url:
            return url
    return None


def excerpt(text):
    """README text with images, HTML tags and link URLs stripped."""
    text = MD_IMG.sub("", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()
