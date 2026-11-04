import re
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
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0 Safari/537.36"
    )
}

# Pagina's die geen echt redactioneel artikel zijn
EXCLUDED_SLUGS = {
    "veelgestelde-vragen",
    "verblijf-en-overnachten",
    "natuur-en-ontspannen",
    "winkelen-en-dwalen",
    "cultuur-en-ontdekken",
    "historie-en-architectuur",
    "familie-en-fun",
    "eten-en-drinken",
}

session = requests.Session()
session.headers.update(HEADERS)


def clean_text(text):
    """Maak tekst netjes voor RSS."""
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


def get_soup(url):
    """Download een webpagina."""
    response = session.get(url, timeout=30)
    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


def meta_content(soup, **attrs):
    """Lees de inhoud van een meta-tag."""
    tag = soup.find("meta", attrs=attrs)

    if tag and tag.get("content"):
        return clean_text(tag["content"])

    return ""


def find_article_urls():
    """Zoek unieke artikel-URL's op de homepage."""
    print("Homepage ophalen...")

    soup = get_soup(HOME_URL)

    urls = []
    seen = set()

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")

        if "/nl/article/" not in href:
            continue

        url = urljoin(BASE_URL, href)
        url = url.split("?")[0].split("#")[0].rstrip("/")

        slug = url.rsplit("/", 1)[-1].lower()

        if slug in EXCLUDED_SLUGS:
            continue

        if url not in seen:
            seen.add(url)
            urls.append(url)

    print(f"{len(urls)} mogelijke artikelen gevonden")

    return urls


def get_title(soup, url):
    """Bepaal de beste titel van het artikel."""

    # 1. OpenGraph-titel
    title = meta_content(
        soup,
        property="og:title"
    )

    if title:
        return clean_title(title)

    # 2. H1
    h1 = soup.find("h1")

    if h1:
        title = clean_text(
            h1.get_text(" ", strip=True)
        )

        if title:
            return clean_title(title)

    # 3. HTML title
    if soup.title:
        title = clean_text(
            soup.title.get_text(" ", strip=True)
        )

        if title:
            return clean_title(title)

    # 4. URL als laatste noodoplossing
    slug = url.rsplit("/", 1)[-1]

    return slug.replace("-", " ").title()


def clean_title(title):
    """Verwijder eventuele sitenaam uit titel."""
    title = clean_text(title)

    replacements = [
        " | Zin in Den Bosch",
        " - Zin in Den Bosch",
    ]

    for value in replacements:
        title = title.replace(value, "")

    return title.strip()


def get_description(soup):
    """Zoek een goede korte beschrijving."""

    # OpenGraph geeft vaak de beste samenvatting
    description = meta_content(
        soup,
        property="og:description"
    )

    if not description:
        description = meta_content(
            soup,
            name="description"
        )

    if description:
        return description[:500]

    # Geen meta-description?
    # Zoek dan eerste bruikbare alinea.
    for paragraph in soup.find_all("p"):
        text = clean_text(
            paragraph.get_text(" ", strip=True)
        )

        if len(text) >= 80:
            return text[:500]

    return ""


def get_image(soup):
    """Zoek de hoofdafbeelding."""

    image = meta_content(
        soup,
        property="og:image"
    )

    if image:
        return urljoin(BASE_URL, image)

    image_tag = soup.find("img", src=True)

    if image_tag:
        return urljoin(
            BASE_URL,
            image_tag["src"]
        )

    return ""


def get_publication_date(soup):
    """Probeer publicatiedatum te vinden."""

    candidates = [
        ("property", "article:published_time"),
        ("name", "date"),
        ("name", "publish-date"),
        ("itemprop", "datePublished"),
    ]

    for attribute, value in candidates:
        tag = soup.find(
            "meta",
            attrs={attribute: value}
        )

        if tag and tag.get("content"):
            raw_date = tag["content"].strip()

            try:
                parsed = datetime.fromisoformat(
                    raw_date.replace(
                        "Z",
                        "+00:00"
                    )
                )

                if parsed.tzinfo is None:
                    parsed = parsed.replace(
                        tzinfo=timezone.utc
                    )

                return parsed

            except ValueError:
                continue

    return None


def get_article(url):
    """Lees titel, beschrijving, afbeelding en datum."""

    print(f"Artikel ophalen: {url}")

    try:
        soup = get_soup(url)

        return {
            "url": url,
            "title": get_title(soup, url),
            "description": get_description(soup),
            "image": get_image(soup),
            "date": get_publication_date(soup),
        }

    except Exception as error:
        print(
            f"Artikel overgeslagen vanwege fout: {error}"
        )

        return None


def create_description(article):
    """Maak de HTML-beschrijving voor RSS."""

    parts = []

    if article["image"]:
        parts.append(
            '<p>'
            f'<img src="{article["image"]}" '
            'alt="" style="max-width:100%;height:auto;">'
            '</p>'
        )

    if article["description"]:
        parts.append(
            f'<p>{article["description"]}</p>'
        )

    parts.append(
        '<p>'
        f'<a href="{article["url"]}">'
        'Lees het volledige artikel op Zin in Den Bosch'
        '</a>'
        '</p>'
    )

    return "".join(parts)


def create_feed(articles):
    """Maak het RSS-document."""

    fg = FeedGenerator()

    fg.title("Zin in Den Bosch")
    fg.description(
        "Onofficiële RSS-feed met artikelen "
        "van Zin in Den Bosch"
    )

    fg.link(
        href=HOME_URL,
        rel="alternate"
    )

    fg.language("nl")

    fg.lastBuildDate(
        datetime.now(timezone.utc)
    )

    # Artikelen met datum eerst
    articles.sort(
        key=lambda article: (
            article["date"]
            if article["date"]
            else datetime.min.replace(
                tzinfo=timezone.utc
            )
        ),
        reverse=True,
    )

    for article in articles:
        entry = fg.add_entry()

        entry.id(article["url"])
        entry.title(article["title"])

        entry.link(
            href=article["url"]
        )

        entry.description(
            create_description(article)
        )

        if article["date"]:
            entry.pubDate(article["date"])

    fg.rss_file(
        OUTPUT_FILE,
        pretty=True
    )


def main():
    print("=== Zin in Den Bosch RSS generator ===")

    urls = find_article_urls()

    articles = []

    for url in urls:
        article = get_article(url)

        if article:
            articles.append(article)

    if not articles:
        raise RuntimeError(
            "Geen artikelen gevonden. "
            "feed.xml wordt niet aangemaakt."
        )

    create_feed(articles)

    print("")
    print(
        f"Klaar: {len(articles)} artikelen "
        "naar feed.xml geschreven."
    )


if __name__ == "__main__":
    main()
