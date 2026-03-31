# Price Tracker

A lightweight REST API that scrapes product prices from any website, tracks their history over time, and sends email alerts when prices drop — built with FastAPI, BeautifulSoup, and SQLite.

---

## What It Does

- **Scrapes** any product URL and extracts the product name and current price
- **Saves** every price check with a timestamp to a local SQLite database
- **Checks prices automatically** every 6 hours via APScheduler
- **Sends email alerts** when a price drops or a target price threshold is reached
- **Dashboard** at `/dashboard` — add, delete, search products and view price charts
- **No cloud or paid service required** — everything runs on your own machine

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Web Scraping | [Requests](https://requests.readthedocs.io/) + [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) |
| Database | SQLite (Python built-in `sqlite3`) |
| ASGI Server | [Uvicorn](https://www.uvicorn.org/) |
| Scheduler | [APScheduler](https://apscheduler.readthedocs.io/) |
| Config | [python-dotenv](https://github.com/theskumar/python-dotenv) |
| Charts | [Chart.js](https://www.chartjs.org/) |

---

## Project Structure

```
price-tracker/
├── api/
│   ├── main.py          # FastAPI app — all REST endpoints + scheduler
│   └── dashboard.html   # Browser dashboard (HTML/CSS/JS)
├── db/
│   └── database.py      # SQLite schema & query helpers
├── notifications/
│   └── email.py         # Gmail SMTP alert sender
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
git clone https://github.com/oykutozluklu/price-tracker.git
cd price-tracker
```

---

### Step 2 — Create a virtual environment

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

> You should see `(venv)` at the start of your terminal line.

---

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4 — Configure environment variables

Open the `.env` file and fill in your values:

```env
# Veritabanı
DB_PATH=prices.db

# Scraper — scraper.py doğrudan çalıştırıldığında kullanılır
TARGET_URL=https://example.com/product

# E-posta bildirimi (Gmail SMTP)
ALERT_EMAIL=bildirim@example.com
GMAIL_USER=sizin@gmail.com
GMAIL_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx
```

> **Gmail App Password:** Google Account → Security → 2-Step Verification → App Passwords → generate one for "Mail".

---

### Step 5 — Start the API server

```bash
python -m uvicorn api.main:app --reload
```

| URL | Description |
|---|---|
| `http://127.0.0.1:8000` | API root |
| `http://127.0.0.1:8000/dashboard` | Browser dashboard |
| `http://127.0.0.1:8000/docs` | Swagger UI |

---

## Dashboard

Open `http://127.0.0.1:8000/dashboard` in your browser.

- **Add a product** — paste any URL and click *Takibe Al*
- **Price table** — current price, % change (↑ red / ↓ green), first recorded date, check count
- **Search** — filter products by name instantly (no API call)
- **Price chart** — click any row to expand a Chart.js line chart of the full price history
- **Set threshold** — click 🔔 to set a target price; a 🎯 badge appears when set
- **Delete** — click 🗑️ to remove a product and its entire history
- **Refresh** — bottom-right button updates the table without reloading the page
- **Mobile** — responsive card layout on screens under 768px

---

## API Reference

### `POST /track`
Scrapes a single URL and saves the price.

```json
// Request
{ "url": "https://example.com/product" }

// Response
{ "url": "...", "name": "Product Name", "price": "1575.00 TRY" }
```

### `POST /track/many`
Track multiple URLs in one request.

```json
// Request
{ "urls": ["https://...", "https://..."] }

// Response
{ "results": [{ "url": "...", "name": "...", "price": "...", "status": "ok" }] }
```

### `GET /products`
Returns all tracked products with latest price, change %, check count, and target price.

### `DELETE /products/{id}`
Permanently deletes a product and its full price history.

### `PATCH /products/{id}/target`
Sets or clears a price threshold for email alerts.

```json
// Request
{ "target_price": 1200.0 }   // or null to remove
```

### `GET /history?url=<url>`
Returns the full price history for a product (newest first).

### `GET /health`
```json
{ "status": "ok" }
```

---

## Automatic Scheduling

The server runs a background job every **6 hours** that:
1. Fetches the current price for every tracked product
2. Saves it to the database
3. Sends a **price drop alert** if the price fell since the last check
4. Sends a **threshold alert** if the price crossed below the target for the first time

---

## Email Alerts

Two types of alerts are sent via Gmail SMTP:

| Trigger | Subject |
|---|---|
| Price dropped vs. previous check | `↓ %5 Fiyat Düştü: Ürün Adı` |
| Price crossed below target threshold | `🎯 Hedef fiyata ulaşıldı: Ürün Adı` |

---

## Customising the Scraper

The selectors in `scraper/scraper.py` first try **JSON-LD structured data** (works on Trendyol and most schema.org-compliant sites), then fall back to CSS selectors.

To support a new site, inspect the page and update the fallback selectors:

```python
price_el = (
    soup.select_one(".new-price")       # site-specific selector
    or soup.select_one("[class*='price']")
)
```

---

## Roadmap

- [x] Scheduled automatic scraping (APScheduler, every 6 hours)
- [x] Price drop alerts via email (Gmail SMTP)
- [x] Target price threshold alerts
- [ ] Per-site selector configuration file
- [ ] Docker support

---

## License

MIT
