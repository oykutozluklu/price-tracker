# Price Tracker

A lightweight REST API that scrapes product prices from any website and tracks their history over time — built with FastAPI, BeautifulSoup, and SQLite.

---

## What It Does

- **Scrapes** any product URL and extracts the product name and current price
- **Saves** every price check with a timestamp to a local SQLite database
- **Exposes a REST API** to track products and query their full price history
- **No cloud or paid service required** — everything runs on your own machine

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Web Scraping | [Requests](https://requests.readthedocs.io/) + [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) |
| Database | SQLite (Python built-in `sqlite3`) |
| ASGI Server | [Uvicorn](https://www.uvicorn.org/) |
| Config | [python-dotenv](https://github.com/theskumar/python-dotenv) |

---

## Project Structure

```
price-tracker/
├── api/
│   └── main.py          # FastAPI app — REST endpoints
├── db/
│   └── database.py      # SQLite schema & query helpers
├── scraper/
│   └── scraper.py       # HTTP fetch + HTML price extraction
├── .env                 # Environment variables (not committed)
├── requirements.txt     # Python dependencies
└── README.md
```

---

## Getting Started

### Prerequisites

- Python **3.10 or higher** — [download here](https://www.python.org/downloads/)
- `pip` — comes bundled with Python automatically

---

### Step 1 — Clone the repository

```bash
git clone https://github.com/your-username/price-tracker.git
cd price-tracker
```

---

### Step 2 — Create a virtual environment

A virtual environment keeps this project's dependencies isolated from other Python projects on your machine.

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

> You should see `(venv)` appear at the start of your terminal line — that means it's active.

---

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This downloads and installs all required libraries (FastAPI, Uvicorn, BeautifulSoup, etc.) listed in `requirements.txt`.

---

### Step 4 — Configure environment variables

Open the `.env` file in the project root and update the values:

```env
# Path where the SQLite database file will be created
DB_PATH=prices.db

# A product URL you want to track (used when running scraper.py directly)
TARGET_URL=https://example.com/product
```

---

### Step 5 — Start the API server

```bash
python -m uvicorn api.main:app --reload
```

- The API will be live at: `http://127.0.0.1:8000`
- Interactive docs (Swagger UI): `http://127.0.0.1:8000/docs`
- The `--reload` flag automatically restarts the server when you save a file

---

## API Reference

### `POST /track`

Scrapes the given product URL, extracts the price, and saves it to the database.

**Request body:**
```json
{
  "url": "https://example.com/product-page"
}
```

**Response:**
```json
{
  "url": "https://example.com/product-page",
  "name": "Example Product",
  "price": "$29.99"
}
```

---

### `GET /history?url=<product-url>`

Returns the full price history for a previously tracked product.

**Example:**
```
GET /history?url=https://example.com/product-page
```

**Response:**
```json
{
  "url": "https://example.com/product-page",
  "history": [
    { "price": "$29.99", "recorded_at": "2026-03-31T10:00:00" },
    { "price": "$34.99", "recorded_at": "2026-03-30T10:00:00" }
  ]
}
```

---

### `GET /health`

Health check — confirms the server is running.

```json
{ "status": "ok" }
```

---

## Customising the Scraper

The selectors in `scraper/scraper.py` are generic defaults. Every website has a different HTML structure, so you will need to update them for each site you want to track.

```python
# scraper/scraper.py
name  = soup.select_one("h1")                  # finds the product title
price = soup.select_one("[class*='price']")    # finds any element whose class contains "price"
```

**How to find the right selectors:**
1. Open the product page in your browser
2. Right-click the price → **Inspect**
3. Note the element's `class` or `id`
4. Update the selector in `scraper.py`

---

## Roadmap

- [ ] Scheduled automatic scraping (cron / background tasks)
- [ ] Price drop alerts via email or webhook
- [ ] Per-site selector configuration file
- [ ] Docker support

---

## License

MIT
