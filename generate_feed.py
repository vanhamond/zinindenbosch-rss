import html
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator


BASE_URL = "https://www.zinindenbosch.nl"
HOME_URL = "https://www.zinindenbosch.nl/nl/page/home"
OUTPUT_FILE = "feed.xml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ZinInDenBoschRSS/1.0; "
        "+https://github.com/)"
    )
}


def get_soup(url):
    """Download a page and return BeautifulSoup."""
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


def clean_text(text):
    """Remove unnecessary whitespace."""
    return " ".join(text.split())


def find_article_links():
    """Find article links on the Zin in Den Bosch homepage."""
    soup = get_soup(HOME_URL)

    articles = []
    seen = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]

        # We only want actual articles
        if "/nl/article/" not in href:
            continue

        url = urljoin(BASE_URL, href)

        # Remove query parameters and anchors
        url = url.split("?")[0]
        url = url.split("#")[0]

        if url in seen:
            continue

        seen.add(url)

        title
