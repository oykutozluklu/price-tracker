import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "prices.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Tabloları oluşturur. Mevcut veritabanlarına eksik sütunları migration ile ekler."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES products(id),
                price TEXT NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

        # Migration: mevcut veritabanlarına target_price sütununu ekle
        # SQLite ALTER TABLE IF NOT EXISTS desteklemediği için try/except kullanılır
        try:
            conn.execute("ALTER TABLE products ADD COLUMN target_price REAL")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Sütun zaten mevcut, sorun yok


def upsert_product(url: str, name: str | None) -> int:
    """Ürün yoksa ekler, varsa adını günceller. Her iki durumda id döner."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO products (url, name) VALUES (?, ?) "
            "ON CONFLICT(url) DO UPDATE SET name = excluded.name",
            (url, name),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM products WHERE url = ?", (url,)).fetchone()
        return row["id"]


def record_price(product_id: int, price: str):
    """Anlık fiyatı tarihçeye kaydeder."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO price_history (product_id, price, recorded_at) VALUES (?, ?, ?)",
            (product_id, price, datetime.utcnow().isoformat()),
        )
        conn.commit()


def get_price_history(url: str) -> list[dict]:
    """Bir ürünün tüm fiyat tarihçesini en yeniden en eskiye döner."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT ph.price, ph.recorded_at
            FROM price_history ph
            JOIN products p ON p.id = ph.product_id
            WHERE p.url = ?
            ORDER BY ph.recorded_at DESC
            """,
            (url,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_all_urls() -> list[str]:
    """Tüm takip edilen URL'leri döner (scheduler için)."""
    with get_connection() as conn:
        rows = conn.execute("SELECT url FROM products ORDER BY id").fetchall()
        return [row["url"] for row in rows]


def get_all_products_basic() -> list[dict]:
    """
    Scheduler için hızlı ürün listesi: id, url, name, target_price.
    Fiyat tarihçesi subquery'leri içermez, daha hızlı çalışır.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, url, name, target_price FROM products ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def get_all_products() -> list[dict]:
    """
    Dashboard için her ürünün özet bilgisini döner:
    en son fiyat, bir önceki fiyat, ilk kayıt tarihi, toplam kontrol sayısı, hedef fiyat.
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                p.id,
                p.url,
                p.name,
                p.target_price,
                -- En son kaydedilen fiyat
                (SELECT ph.price FROM price_history ph
                 WHERE ph.product_id = p.id
                 ORDER BY ph.recorded_at DESC LIMIT 1) AS latest_price,
                -- Bir önceki fiyat (değişim hesabı için)
                (SELECT ph.price FROM price_history ph
                 WHERE ph.product_id = p.id
                 ORDER BY ph.recorded_at DESC LIMIT 1 OFFSET 1) AS previous_price,
                -- İlk kayıt tarihi
                (SELECT ph.recorded_at FROM price_history ph
                 WHERE ph.product_id = p.id
                 ORDER BY ph.recorded_at ASC LIMIT 1) AS first_recorded_at,
                -- Toplam kontrol sayısı
                (SELECT COUNT(*) FROM price_history ph
                 WHERE ph.product_id = p.id) AS check_count
            FROM products p
            ORDER BY p.id
        """).fetchall()
        return [dict(row) for row in rows]


def delete_product(product_id: int) -> bool:
    """
    Ürünü ve tüm fiyat geçmişini kalıcı olarak siler.
    Başarılıysa True, ürün bulunamazsa False döner.
    """
    with get_connection() as conn:
        # Önce tarihçeyi sil (foreign key kısıtı)
        conn.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
        # Sonra ürünü sil
        result = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        return result.rowcount > 0


def set_target_price(product_id: int, target_price: float | None) -> bool:
    """
    Ürünün hedef fiyatını günceller.
    target_price=None ile mevcut eşiği kaldırabilirsin.
    Başarılıysa True, ürün bulunamazsa False döner.
    """
    with get_connection() as conn:
        result = conn.execute(
            "UPDATE products SET target_price = ? WHERE id = ?",
            (target_price, product_id),
        )
        conn.commit()
        return result.rowcount > 0


if __name__ == "__main__":
    init_db()
    print(f"Veritabanı hazır: {DB_PATH}")
