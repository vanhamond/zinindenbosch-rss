import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from urllib.parse import urljoin

HOME_URL = "https://www.zinindenbosch.nl/nl/page/home"
BASE_URL = "https://www.zinindenbosch.nl"

headers = {
    "User-Agent": "Mozilla/5.0"
}

print("Zin in Den Bosch ophalen...")

response = requests.get(
    HOME_URL,
    headers=headers,
    timeout=30
)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

articles = []
seen = set()

for link in soup.find_all("a", href=True):
    href = link["href"]

    if "/nl/article/" in href:
        url = urljoin(BASE_URL, href)
        url = url.split("?")[0].split("#")[0]

        if url not in seen:
            seen.add(url)

            title = " ".join(
                link.get_text(" ", strip=True).split()
            )

            if not title:
                title = url.split("/")[-1].replace("-", " ").title()

            articles.append((title, url))

print(f"{len(articles)} artikelen gevonden")

fg = FeedGenerator()

fg.title("Zin in Den Bosch")
fg.description(
    "Onofficiele RSS-feed voor artikelen van Zin in Den Bosch"
)
fg.link(href=HOME_URL, rel="alternate")
fg.language("nl")

for title, url in articles:
    entry = fg.add_entry()
    entry.id(url)
    entry.title(title)
    entry.link(href=url)
    entry.description(
        f'Lees het volledige artikel op Zin in Den Bosch: {url}'
    )

fg.rss_file("feed.xml", pretty=True)

print("feed.xml succesvol aangemaakt")
