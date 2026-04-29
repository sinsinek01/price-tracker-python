# E-Commerce Price Tracker & Auto-Alert System

A fully automated price monitoring system that tracks product listings across multiple Turkish e-commerce platforms and sends instant email alerts when prices drop below your target.

## Features

- Multi-site scraping — Trendyol, Hepsiburada, and any custom site
- SQLite database for full price history
- Automatic email alerts via Gmail SMTP
- Runs 24/7 on a configurable schedule
- Smart price parsing — handles any currency format (₺, $, €)
- Anti-bot headers to avoid detection

## Tech Stack

- Python 3.10+
- BeautifulSoup4
- SQLite3
- Selenium (for JS-heavy sites)
- smtplib (Gmail SMTP)

## Setup

1. Clone the repo
```bash
git clone https://github.com/yourusername/price-tracker-python
cd price-tracker-python
```

2. Install dependencies
```bash
pip install requests beautifulsoup4
```

3. Configure your settings in `price_tracker.py`
```python
GMAIL_ADRES = "your@gmail.com"
GMAIL_SIFRE = "your-app-password"   # Gmail app password
KONTROL_ARALIGI = 3600              # check interval in seconds

URUNLER = [
    {
        "ad"         : "iPhone 15 Pro",
        "url"        : "https://www.trendyol.com/...",
        "hedef_fiyat": 45000,
        "site"       : "trendyol"
    },
]
```

4. Run
```bash
python price_tracker.py
```

## How It Works

```
Every N minutes
      ↓
Fetch product page
      ↓
Parse current price
      ↓
Save to SQLite DB
      ↓
Price ≤ target? → Send email alert
```

## Sample Output

```
[Tur 1] 2026-04-28 22:00:00
────────────────────────────────────────
  Kontrol ediliyor: iPhone 15 Pro
  ✔ Fiyat: 44,990.00 TL (Hedef: 45,000.00 TL)
  📧 Alert maili gönderildi!

  Kontrol ediliyor: Samsung 4K Monitor
  ✔ Fiyat: 8,450.00 TL (Hedef: 8,000.00 TL)
```

## Author

**Hacer B.** — Python Automation & Web Scraping Expert

- Upwork: https://www.upwork.com/freelancers/~01ff7cdd896ef9c905
- GitHub: https://github.com/Hacer-B
