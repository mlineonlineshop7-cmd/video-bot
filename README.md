# Video İndirme Telegram Botu

Kullanıcı YouTube, Instagram, TikTok veya Twitter (X) linki gönderdiğinde
videoyu indirip Telegram üzerinden geri gönderen basit bir bot.

## 1. Telegram Bot Oluşturma

1. Telegram'da **@BotFather** ile konuşma başlat.
2. `/newbot` komutunu gönder, bot için bir isim ve kullanıcı adı belirle.
3. BotFather sana bir **token** verecek (örn. `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`).
   Bu tokeni kimseyle paylaşma.

## 2. VPS Kurulumu (Ubuntu/Debian örneği)

```bash
# Sistem paketlerini güncelle
sudo apt update && sudo apt install -y python3 python3-pip python3-venv ffmpeg

# Proje klasörünü sunucuna kopyala (scp, git, vs. ile) sonra içine gir
cd video-bot

# Sanal ortam oluştur
python3 -m venv venv
source venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt
```

> **ffmpeg önemli:** yt-dlp bazı videolarda ses ve görüntüyü ayrı indirip
> birleştirmek için ffmpeg kullanır. Kurulu olmazsa bazı videolar
> indirilemez.

## 3. Botu Çalıştırma

Token'ı ortam değişkeni olarak ver (koda YAZMAYIN):

```bash
export TELEGRAM_BOT_TOKEN="BotFather'dan aldığın token"
python3 bot.py
```

Bot çalışmaya başladığında Telegram'da botunu bulup `/start` yazabilirsin,
ardından bir video linki gönderdiğinde videoyu sana geri gönderecektir.

## 4. Sunucuda Kalıcı Çalıştırma (systemd ile)

Terminali kapatınca botun durmaması için bir systemd servisi oluşturmak
iyi bir yöntemdir:

```bash
sudo nano /etc/systemd/system/videobot.service
```

İçeriği:

```ini
[Unit]
Description=Telegram Video Indirme Botu
After=network.target

[Service]
Type=simple
User=YOUR_LINUX_USER
WorkingDirectory=/path/to/video-bot
Environment="TELEGRAM_BOT_TOKEN=BotFather_tokenin"
ExecStart=/path/to/video-bot/venv/bin/python3 bot.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Sonra:

```bash
sudo systemctl daemon-reload
sudo systemctl enable videobot
sudo systemctl start videobot
sudo systemctl status videobot   # çalışıp çalışmadığını kontrol et
journalctl -u videobot -f        # canlı logları izle
```

## 5. Önemli Sınırlamalar

- **Dosya boyutu limiti:** Telegram'ın resmi Bot API'si (bulut sunucuları)
  bot üzerinden gönderilecek dosyalarda **~50MB** sınırı koyar. Bu koddaki
  `MAX_FILE_SIZE_MB` değişkeni bunu kontrol eder. Daha büyük videolar
  göndermek istersen kendi **Local Bot API Server**'ını kurman gerekir
  (bkz. https://github.com/tdlib/telegram-bot-api). Bu, VPS'inde ayrı bir
  servis olarak çalışır ve limiti 2GB'a çıkarır.
- **Instagram/TikTok özel hesaplar:** Özel (gizli) hesap içerikleri veya
  giriş gerektiren içerikler indirilemeyebilir. Gerekirse yt-dlp'nin
  `cookiefile` özelliğiyle tarayıcı çerezlerinizi ekleyebilirsiniz
  (yt-dlp dokümantasyonuna bakın).
- **Platformlar değişebilir:** YouTube, Instagram, TikTok ve Twitter
  zaman zaman indirme yöntemlerini değiştirir. Bot çalışmazsa önce
  `pip install -U yt-dlp` ile yt-dlp'yi güncelleyin — yt-dlp bu tür
  değişikliklere sık sık güncelleme çıkarır.
- **Telif hakkı:** İndirilen içerikleri yalnızca kişisel kullanım ve
  ilgili platformun kullanım şartlarına uygun şekilde kullanın.

## 6. Sorun Giderme

| Sorun | Çözüm |
|---|---|
| `TELEGRAM_BOT_TOKEN ortam değişkeni bulunamadı` | `export TELEGRAM_BOT_TOKEN=...` komutunu çalıştırdığınızdan emin olun |
| Video indirilemiyor / hata veriyor | `pip install -U yt-dlp` ile güncelleyin |
| Ses/görüntü birleşmiyor | `ffmpeg` kurulu mu kontrol edin: `ffmpeg -version` |
| "Video çok büyük" hatası | Local Bot API Server kurun ya da daha düşük kalite formatı seçin |
