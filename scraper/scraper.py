import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()


def fetch_price(url: str) -> dict:
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    })
    response = session.get(url, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # 1) Önce JSON-LD structured data dene — en temiz kaynak
    name, price = _parse_jsonld(soup)

    # 2) JSON-LD yoksa HTML selector'larına dön
    if not name:
        name_el = soup.select_one("h1")
        name = name_el.get_text(strip=True) if name_el else None

    if not price:
        price_el = (
            soup.select_one(".new-price")   # Trendyol indirimli fiyat
            or soup.select_one(".prc-dsc")  # alternatif Trendyol sınıfı
            or soup.select_one("[class*='price']")
        )
        price = price_el.get_text(strip=True) if price_el else None

    return {"url": url, "name": name, "price": price}


def _parse_jsonld(soup: BeautifulSoup):
    """Schema.org JSON-LD bloklarından ürün adı ve fiyatı çeker."""
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        if data.get("@type") not in ("Product", "ProductGroup"):
            continue

        name = data.get("name")

        # offers tek nesne ya da liste olabilir
        offers = data.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price = None
        if isinstance(offers, dict):
            value = offers.get("price") or offers.get("lowPrice")
            currency = offers.get("priceCurrency", "")
            if value:
                price = f"{value} {currency}".strip()

        if name or price:
            return name, price

    return None, None


if __name__ == "__main__":
    url = os.getenv("TARGET_URL", "")
    if url:
        result = fetch_price(url)
        print(result)
    else:
        print("TARGET_URL not set in .env")
