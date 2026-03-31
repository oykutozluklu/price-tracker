import os
import re
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Proje kökünü Python path'ine ekle
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from db.database import (
    init_db,
    upsert_product,
    record_price,
    get_price_history,
    get_all_products,
    get_all_products_basic,
    get_all_urls,
    delete_product,
    set_target_price,
)
from scraper.scraper import fetch_price
from notifications.email import send_price_alert, send_threshold_alert

# ---------- Scheduler ----------
scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")


def check_all_prices():
    """
    Her 6 saatte bir otomatik çalışır.
    - Tüm ürünlerin güncel fiyatını çeker ve kaydeder.
    - Fiyat bir önceki kayda göre düştüyse genel bildirim gönderir.
    - Fiyat hedef eşiğin altına ilk kez düştüyse eşik bildirimi gönderir.
    """
    products = get_all_products_basic()
    if not products:
        return

    print(f"[Scheduler] {len(products)} ürün kontrol ediliyor…")

    for p in products:
        url = p["url"]
        try:
            # Kaydetmeden ÖNCE mevcut son fiyatı al (karşılaştırma için)
            history        = get_price_history(url)
            son_fiyat_str  = history[0]["price"] if history else None

            # Sayfadan yeni fiyatı çek
            data = fetch_price(url)
            if not data.get("price"):
                print(f"[Scheduler] Fiyat bulunamadı: {url[:70]}")
                continue

            yeni_val = parse_price_value(data["price"])

            # Veritabanına kaydet
            product_id = upsert_product(url, data.get("name"))
            record_price(product_id, data["price"])

            # ── Genel düşüş bildirimi ──────────────────────────────
            if son_fiyat_str and yeni_val:
                eski_val = parse_price_value(son_fiyat_str)
                if eski_val and yeni_val < eski_val and eski_val > 0:
                    change_pct = round((yeni_val - eski_val) / eski_val * 100, 1)
                    send_price_alert(
                        url=url,
                        name=data.get("name"),
                        old_price=son_fiyat_str,
                        new_price=data["price"],
                        change_pct=change_pct,
                    )

            # ── Hedef fiyat eşiği bildirimi ───────────────────────
            # Yalnızca eşik tanımlıysa VE yeni fiyat eşiğin altındaysa
            # VE önceki fiyat eşiğin üstündeyse (ilk geçiş anı) bildir
            target = p.get("target_price")
            if target and yeni_val and yeni_val <= target:
                eski_val = parse_price_value(son_fiyat_str) if son_fiyat_str else None
                if eski_val is None or eski_val > target:
                    send_threshold_alert(
                        url=url,
                        name=data.get("name"),
                        new_price=data["price"],
                        target_price=target,
                    )

            print(f"[Scheduler] ✓ {url[:60]} → {data['price']}")

        except Exception as exc:
            print(f"[Scheduler] Hata ({url[:60]}): {exc}")


# ---------- Uygulama yaşam döngüsü ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: DB init + scheduler başlat. Shutdown: scheduler durdur."""
    init_db()
    scheduler.add_job(
        check_all_prices,
        trigger="interval",
        hours=6,
        id="auto_price_check",
        max_instances=1,          # Aynı anda sadece bir çalışma
        misfire_grace_time=3600,  # 1 saate kadar gecikmiş çalışmayı tolere et
    )
    scheduler.start()
    print("[Scheduler] Başlatıldı — her 6 saatte bir çalışacak.")
    yield
    scheduler.shutdown()
    print("[Scheduler] Durduruldu.")


app = FastAPI(title="Price Tracker API", lifespan=lifespan)


# ---------- Yardımcı: fiyat stringinden float çıkar ----------
def parse_price_value(price_str: str) -> float | None:
    """
    "1575.00 TRY" → 1575.0
    "1.575,00 TL" → 1575.0
    "$29.99"       → 29.99
    Tanınamayan formatlarda None döner.
    """
    if not price_str:
        return None
    match = re.search(r"[\d]+(?:[.,][\d]+)*", price_str)
    if not match:
        return None
    raw = match.group(0)
    if "," in raw:
        # Türkçe format: binlik=nokta, ondalık=virgül → 1.575,00 → 1575.00
        raw = raw.replace(".", "").replace(",", ".")
    elif raw.count(".") > 1:
        # Çok nokta → binlik ayırıcı: 1.575.000 → 1575000
        raw = raw.replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return None


# ---------- Request modelleri ----------
class TrackRequest(BaseModel):
    url: HttpUrl


class TrackManyRequest(BaseModel):
    urls: list[HttpUrl]


class TargetPriceRequest(BaseModel):
    target_price: float | None  # None göndererek eşiği kaldırabilirsin


# ---------- Endpoint: tek ürün takip ----------
@app.post("/track")
def track(request: TrackRequest):
    """Tek URL'den fiyat çeker ve kaydeder."""
    url = str(request.url)
    try:
        data = fetch_price(url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Scrape başarısız: {exc}")

    if not data.get("price"):
        raise HTTPException(status_code=422, detail="Sayfadan fiyat çıkarılamadı")

    product_id = upsert_product(url, data.get("name"))
    record_price(product_id, data["price"])

    return {"url": url, "name": data.get("name"), "price": data["price"]}


# ---------- Endpoint: çoklu ürün takip ----------
@app.post("/track/many")
def track_many(request: TrackManyRequest):
    """
    Birden fazla URL'i tek seferde takibe ekler.
    Her URL için bağımsız sonuç döner; bir hata diğerlerini durdurmaz.
    """
    results = []
    for url_obj in request.urls:
        url = str(url_obj)
        try:
            data = fetch_price(url)
            if not data.get("price"):
                results.append({"url": url, "status": "hata", "detail": "Fiyat bulunamadı"})
                continue
            product_id = upsert_product(url, data.get("name"))
            record_price(product_id, data["price"])
            results.append({"url": url, "name": data.get("name"),
                            "price": data["price"], "status": "ok"})
        except Exception as exc:
            results.append({"url": url, "status": "hata", "detail": str(exc)})

    return {"results": results}


# ---------- Endpoint: fiyat tarihçesi ----------
@app.get("/history")
def history(url: str):
    """Bir ürünün tüm fiyat tarihçesini döner."""
    rows = get_price_history(url)
    if not rows:
        raise HTTPException(status_code=404, detail="Bu URL için tarihçe bulunamadı")
    return {"url": url, "history": rows}


# ---------- Endpoint: tüm ürünler (dashboard için) ----------
@app.get("/products")
def get_products():
    """
    Dashboard tablosu için tüm ürünleri özetler:
    güncel fiyat, değişim yüzdesi, ilk kayıt, kontrol sayısı, hedef fiyat.
    """
    products = get_all_products()
    result = []
    for p in products:
        # Son iki fiyat arasındaki yüzde değişim
        change_pct = None
        if p["latest_price"] and p["previous_price"]:
            eski = parse_price_value(p["previous_price"])
            yeni = parse_price_value(p["latest_price"])
            if eski and yeni and eski > 0:
                change_pct = round((yeni - eski) / eski * 100, 1)

        result.append({
            "id":                p["id"],
            "url":               p["url"],
            "name":              p["name"],
            "latest_price":      p["latest_price"],
            "previous_price":    p["previous_price"],
            "first_recorded_at": p["first_recorded_at"],
            "check_count":       p["check_count"],
            "change_pct":        change_pct,
            "target_price":      p["target_price"],
        })
    return result


# ---------- Endpoint: ürün sil ----------
@app.delete("/products/{product_id}")
def remove_product(product_id: int):
    """Ürünü ve tüm fiyat geçmişini kalıcı olarak siler."""
    success = delete_product(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    return {"deleted": product_id}


# ---------- Endpoint: hedef fiyat belirle ----------
@app.patch("/products/{product_id}/target")
def update_target(product_id: int, request: TargetPriceRequest):
    """Ürün için fiyat eşiği belirler. target_price=null ile kaldırılabilir."""
    success = set_target_price(product_id, request.target_price)
    if not success:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    return {"product_id": product_id, "target_price": request.target_price}


# ---------- Endpoint: dashboard HTML ----------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """Fiyat takip panelini HTML olarak sunar."""
    html_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


# ---------- Endpoint: sağlık kontrolü ----------
@app.get("/health")
def health():
    return {"status": "ok"}
