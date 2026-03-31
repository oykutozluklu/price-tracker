import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")


def _send(subject: str, plain: str, html: str):
    """Ortak SMTP gönderme yardımcısı. Ayarlar eksikse sessizce atlar."""
    if not all([GMAIL_USER, GMAIL_APP_PASSWORD, ALERT_EMAIL]):
        print("[E-posta] Ayarlar eksik (.env), bildirim atlandı.")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = ALERT_EMAIL
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_USER, ALERT_EMAIL, msg.as_string())
        print(f"[E-posta] Gönderildi → {ALERT_EMAIL} | Konu: {subject}")
    except Exception as exc:
        print(f"[E-posta] Gönderme hatası: {exc}")


def send_price_alert(
    url: str,
    name: str | None,
    old_price: str,
    new_price: str,
    change_pct: float,
):
    """Genel fiyat düşüşü bildirimi (önceki fiyata göre değişim)."""
    label      = name or url
    abs_change = abs(change_pct)

    plain = f"""Fiyat Düşüş Bildirimi

Ürün       : {label}
URL        : {url}
Eski fiyat : {old_price}
Yeni fiyat : {new_price}
Değişim    : ↓ %{abs_change}

Bu bildirimi Price Tracker uygulaması gönderdi.
"""
    html = f"""<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#fff;border-radius:12px;
              border:1px solid #e5e7eb;overflow:hidden;">
    <div style="background:#16a34a;padding:24px 28px;">
      <h1 style="margin:0;color:#fff;font-size:20px;">Fiyat Düştü ↓</h1>
      <p style="margin:6px 0 0;color:#dcfce7;font-size:14px;">Price Tracker bildirimi</p>
    </div>
    <div style="padding:28px;">
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <tr style="background:#f9fafb;">
          <td style="padding:10px 14px;color:#6b7280;width:120px;">Ürün</td>
          <td style="padding:10px 14px;font-weight:600;">{label}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;color:#6b7280;">Eski fiyat</td>
          <td style="padding:10px 14px;color:#6b7280;text-decoration:line-through;">{old_price}</td>
        </tr>
        <tr style="background:#f0fdf4;">
          <td style="padding:10px 14px;color:#6b7280;">Yeni fiyat</td>
          <td style="padding:10px 14px;font-weight:700;font-size:18px;color:#16a34a;">{new_price}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;color:#6b7280;">Değişim</td>
          <td style="padding:10px 14px;color:#16a34a;font-weight:600;">↓ %{abs_change}</td>
        </tr>
      </table>
      <a href="{url}" style="display:inline-block;margin-top:24px;padding:11px 22px;
         background:#6366f1;color:#fff;border-radius:8px;text-decoration:none;
         font-size:14px;font-weight:500;">Ürüne Git →</a>
    </div>
    <div style="padding:16px 28px;background:#f9fafb;border-top:1px solid #e5e7eb;">
      <p style="margin:0;font-size:12px;color:#9ca3af;">Price Tracker tarafından otomatik gönderildi.</p>
    </div>
  </div>
</body></html>"""

    _send(f"↓ %{abs_change} Fiyat Düştü: {label}", plain, html)


def send_threshold_alert(
    url: str,
    name: str | None,
    new_price: str,
    target_price: float,
):
    """
    Fiyat hedef eşiğin altına ilk kez düştüğünde gönderilir.
    Her scheduler çalışmasında değil, yalnızca eşik çizgisi geçildiğinde tetiklenir.
    """
    label = name or url

    plain = f"""Hedef Fiyata Ulaşıldı!

Ürün         : {label}
URL          : {url}
Hedef fiyat  : {target_price} TRY
Güncel fiyat : {new_price}

Fiyat belirlediğiniz eşiğin altına düştü.
Bu bildirimi Price Tracker uygulaması gönderdi.
"""
    html = f"""<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#fff;border-radius:12px;
              border:1px solid #e5e7eb;overflow:hidden;">
    <div style="background:#6366f1;padding:24px 28px;">
      <h1 style="margin:0;color:#fff;font-size:20px;">🎯 Hedef Fiyata Ulaşıldı!</h1>
      <p style="margin:6px 0 0;color:#e0e7ff;font-size:14px;">Price Tracker fiyat eşiği bildirimi</p>
    </div>
    <div style="padding:28px;">
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <tr style="background:#f9fafb;">
          <td style="padding:10px 14px;color:#6b7280;width:130px;">Ürün</td>
          <td style="padding:10px 14px;font-weight:600;">{label}</td>
        </tr>
        <tr style="background:#f5f3ff;">
          <td style="padding:10px 14px;color:#6b7280;">Hedef fiyat</td>
          <td style="padding:10px 14px;font-weight:600;color:#6366f1;">{target_price} TRY</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;color:#6b7280;">Güncel fiyat</td>
          <td style="padding:10px 14px;font-weight:700;font-size:18px;color:#16a34a;">{new_price}</td>
        </tr>
      </table>
      <a href="{url}" style="display:inline-block;margin-top:24px;padding:11px 22px;
         background:#6366f1;color:#fff;border-radius:8px;text-decoration:none;
         font-size:14px;font-weight:500;">Ürüne Git →</a>
    </div>
    <div style="padding:16px 28px;background:#f9fafb;border-top:1px solid #e5e7eb;">
      <p style="margin:0;font-size:12px;color:#9ca3af;">Price Tracker tarafından otomatik gönderildi.</p>
    </div>
  </div>
</body></html>"""

    _send(f"🎯 Hedef fiyata ulaşıldı: {label}", plain, html)
