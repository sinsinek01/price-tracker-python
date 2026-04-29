"""
E-Commerce Price Tracker & Alert System
========================================
Tracks product prices from multiple e-commerce sites,
stores history in SQLite, and sends email alerts when
prices drop below your target.

Author  : Hacer B. — Python Automation Expert
Profile : https://www.upwork.com/freelancers/~01ff7cdd896ef9c905
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import smtplib
import time
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─── CONFIG ────────────────────────────────────────────────

GMAIL_ADRES = "your@gmail.com"
GMAIL_SIFRE = "your-app-password"

KONTROL_ARALIGI = 3600  # kaç saniyede bir kontrol et (3600 = 1 saat)

# Takip etmek istediğin ürünler
URUNLER = [
    {
        "ad"        : "iPhone 15 Pro",
        "url"       : "https://www.trendyol.com/apple/iphone-15-pro-p-123456",
        "hedef_fiyat": 45000,   # bu fiyatın altına düşünce mail at
        "site"      : "trendyol"
    },
    {
        "ad"        : "Samsung 4K Monitor",
        "url"       : "https://www.hepsiburada.com/samsung-monitor-p-123",
        "hedef_fiyat": 8000,
        "site"      : "hepsiburada"
    },
]

# ─── DATABASE ──────────────────────────────────────────────

def db_baslat():
    """SQLite veritabanını oluşturur."""
    conn = sqlite3.connect("fiyat_takip.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fiyatlar (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            urun_adi  TEXT,
            fiyat     REAL,
            para_birimi TEXT DEFAULT 'TRY',
            url       TEXT,
            tarih     TEXT
        )
    """)
    conn.commit()
    return conn


def fiyat_kaydet(conn, urun_adi, fiyat, url):
    conn.execute(
        "INSERT INTO fiyatlar (urun_adi, fiyat, url, tarih) VALUES (?, ?, ?, ?)",
        (urun_adi, fiyat, url, datetime.now().isoformat())
    )
    conn.commit()


def son_fiyat_al(conn, urun_adi):
    """En son kaydedilen fiyatı döndürür."""
    cursor = conn.execute(
        "SELECT fiyat FROM fiyatlar WHERE urun_adi=? ORDER BY tarih DESC LIMIT 1",
        (urun_adi,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def fiyat_gecmisi(conn, urun_adi, gun=7):
    """Son N günün fiyat geçmişini döndürür."""
    cursor = conn.execute(
        """SELECT fiyat, tarih FROM fiyatlar
           WHERE urun_adi=?
           ORDER BY tarih DESC LIMIT ?""",
        (urun_adi, gun * 24)
    )
    return cursor.fetchall()

# ─── SCRAPERS ──────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fiyat_parse(metin):
    """'45.990,00 TL' gibi metni float'a çevirir."""
    import re
    rakamlar = re.sub(r"[^\d,.]", "", metin)
    rakamlar = rakamlar.replace(".", "").replace(",", ".")
    try:
        return float(rakamlar)
    except:
        return None


def trendyol_fiyat_cek(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        # Trendyol fiyat seçiciler
        for selector in [
            "span.prc-dsc",
            "span.product-price",
            '[class*="discountedPrice"]',
            '[class*="price"]',
        ]:
            elem = soup.select_one(selector)
            if elem:
                fiyat = fiyat_parse(elem.get_text())
                if fiyat:
                    return fiyat
    except Exception as e:
        print(f"  Trendyol hata: {e}")
    return None


def hepsiburada_fiyat_cek(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        for selector in [
            "span[data-bind*='finalPrice']",
            "span.product-price",
            '[class*="price"]',
        ]:
            elem = soup.select_one(selector)
            if elem:
                fiyat = fiyat_parse(elem.get_text())
                if fiyat:
                    return fiyat
    except Exception as e:
        print(f"  Hepsiburada hata: {e}")
    return None


def genel_fiyat_cek(url):
    """Bilinmeyen sitelerde genel fiyat çekmeyi dener."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        for selector in [
            '[class*="price"]', '[class*="fiyat"]',
            '[itemprop="price"]', '[class*="cost"]',
        ]:
            elem = soup.select_one(selector)
            if elem:
                fiyat = fiyat_parse(elem.get_text())
                if fiyat and fiyat > 1:
                    return fiyat
    except Exception as e:
        print(f"  Genel hata: {e}")
    return None


def fiyat_cek(urun):
    site = urun.get("site", "").lower()
    if "trendyol" in site or "trendyol" in urun["url"]:
        return trendyol_fiyat_cek(urun["url"])
    elif "hepsiburada" in site or "hepsiburada" in urun["url"]:
        return hepsiburada_fiyat_cek(urun["url"])
    else:
        return genel_fiyat_cek(urun["url"])

# ─── EMAIL ALERT ───────────────────────────────────────────

def alert_mail_gonder(urun_adi, mevcut_fiyat, hedef_fiyat, url):
    konu = f"🔔 Fiyat Düştü: {urun_adi} — {mevcut_fiyat:,.0f} TL"
    icerik = f"""Merhaba!

Takip ettiğiniz ürünün fiyatı hedef fiyatın altına düştü.

Ürün       : {urun_adi}
Şu an fiyat: {mevcut_fiyat:,.2f} TL
Hedef fiyat: {hedef_fiyat:,.2f} TL
Tasarruf   : {hedef_fiyat - mevcut_fiyat:,.2f} TL

Ürüne gitmek için: {url}

Bu alert Python Price Tracker tarafından gönderildi.
"""
    msg = MIMEMultipart()
    msg["Subject"] = konu
    msg["From"]    = GMAIL_ADRES
    msg["To"]      = GMAIL_ADRES
    msg.attach(MIMEText(icerik, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_ADRES, GMAIL_SIFRE)
        s.sendmail(GMAIL_ADRES, GMAIL_ADRES, msg.as_string())
    print(f"  📧 Alert maili gönderildi!")

# ─── RAPOR ─────────────────────────────────────────────────

def rapor_yazdir(conn):
    print("\n" + "=" * 55)
    print("  FİYAT RAPORU")
    print("=" * 55)
    for urun in URUNLER:
        ad      = urun["ad"]
        hedef   = urun["hedef_fiyat"]
        gecmis  = fiyat_gecmisi(conn, ad, gun=1)
        if gecmis:
            son   = gecmis[0][0]
            durum = "✅ HEDEF ALTI" if son <= hedef else "⏳ Bekleniyor"
            print(f"\n  {ad}")
            print(f"    Son fiyat : {son:,.2f} TL")
            print(f"    Hedef     : {hedef:,.2f} TL")
            print(f"    Durum     : {durum}")

# ─── ANA DÖNGÜ ─────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  E-COMMERCE PRICE TRACKER — Hacer B.")
    print("=" * 55)
    print(f"  {len(URUNLER)} ürün takip ediliyor")
    print(f"  Kontrol aralığı: {KONTROL_ARALIGI // 60} dakika")
    print("=" * 55)

    conn = db_baslat()
    tur  = 0

    while True:
        tur += 1
        zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[Tur {tur}] {zaman}")
        print("─" * 40)

        for urun in URUNLER:
            ad     = urun["ad"]
            hedef  = urun["hedef_fiyat"]
            print(f"\n  Kontrol ediliyor: {ad}")

            fiyat = fiyat_cek(urun)

            if fiyat:
                fiyat_kaydet(conn, ad, fiyat, urun["url"])
                print(f"  ✔ Fiyat: {fiyat:,.2f} TL (Hedef: {hedef:,.2f} TL)")

                # Alert kontrolü
                if fiyat <= hedef:
                    print(f"  🎯 HEDEF FİYATA ULAŞILDI!")
                    try:
                        alert_mail_gonder(ad, fiyat, hedef, urun["url"])
                    except Exception as e:
                        print(f"  ⚠ Mail gönderilemedi: {e}")
            else:
                print(f"  ⚠ Fiyat çekilemedi")

            time.sleep(2)

        rapor_yazdir(conn)
        print(f"\n  ⏳ {KONTROL_ARALIGI // 60} dakika sonra tekrar kontrol edilecek...")
        time.sleep(KONTROL_ARALIGI)


if __name__ == "__main__":
    main()