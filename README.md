# Telegram Trading Bot Indodax

Bot trading Telegram multi-user untuk market Indodax dengan arsitektur service-oriented. Repository ini menyediakan tiga service utama: core API (FastAPI), Telegram bot (aiogram), dan worker strategi (APScheduler). Semua komponen siap dijalankan melalui Docker.

## Fitur Utama

- Integrasi penuh dengan Indodax Public & Private API (HMAC-SHA512, nonce via Redis).
- Manajemen user multi-akun dengan penyimpanan API key terenkripsi (AES-256-GCM).
- Trading manual melalui Telegram: cek harga, buat order market/limit, kelola open order.
- Strategi otomatis: Dollar Cost Averaging (DCA), Grid trading, dan Take-Profit/Stop-Loss.
- Portfolio & PNL agregasi berdasarkan data real-time Indodax.
- Price alert dan notifikasi real-time ke Telegram (worker → webhook internal bot).
- Konsumsi data harga via WebSocket Indodax (fallback REST) untuk strategi & alert.
- Dead man switch melalui worker logging dan strategi pause jika terjadi error masal.

## Struktur Proyek

```
├── bot/                # Telegram bot service (aiogram)
├── core/               # FastAPI trading core + integrasi Indodax
├── worker/             # Scheduler dan task strategi otomatis
├── tests/              # Unit tests
├── alembic/            # Migrasi database
├── docker/             # Dockerfile tiap service
├── scripts/            # Entrypoint container
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## Persiapan Lingkungan

1. **Clone repo**
   ```bash
   git clone https://github.com/your-org/indodax-bot.git
   cd indodax-bot
   ```

2. **Salin konfigurasi**
   ```bash
   cp .env.example .env
   ```

3. **Isi variabel lingkungan**
   - `TELEGRAM_BOT_TOKEN`: token BotFather.
   - `APP_SECRET_KEY`: minimal 32 karakter untuk enkripsi AES-GCM.
   - `DATABASE_URL`, `REDIS_URL`: default sudah menunjuk ke service docker-compose.
   - `CORE_API_BASE_URL`: gunakan `http://trading-core-api:8000` untuk komunikasi antar service.
   - `INTERNAL_AUTH_TOKEN`: shared secret antara core ↔ worker ↔ bot untuk endpoint internal.
   - `BOT_INTERNAL_WEBHOOK`: URL internal bot (`http://telegram-bot-service:8080/internal/notify`).
   - `BOT_INTERNAL_HOST` & `BOT_INTERNAL_PORT`: binding server internal bot (default 0.0.0.0:8080).
   - `CORE_API_INTERNAL_TOKEN`: token internal yang sama dengan `INTERNAL_AUTH_TOKEN`.
   - `PRICE_FEED_WS_URL`: endpoint websocket harga Indodax.
   - `USER_TOKEN_TTL_SECONDS`, `USER_TOKEN_ROTATION_THRESHOLD_SECONDS`, `USER_TOKEN_REFRESH_THRESHOLD_SECONDS`: kontrol masa berlaku, ambang rotasi core, dan ambang refresh otomatis di bot.

4. **Jalankan dengan Docker**
   ```bash
   docker-compose up -d --build
   ```

5. **Migrasi database**
   Container core akan menjalankan `alembic upgrade head` otomatis saat start.

## Cara Menambahkan API Key Indodax

1. Buat API key baru di Indodax dengan permission **trade** dan **info** (tanpa withdraw).
2. Buka chat dengan bot di Telegram, jalankan `/link` dan ikuti instruksi.
3. Bot akan memvalidasi API key dengan `getInfo`, menyimpan versi terenkripsi, dan siap trading.
4. Setiap kali proses link berhasil, core API mengeluarkan token akses pengguna yang disimpan bot dalam bentuk terenkripsi di Redis (dengan TTL yang dapat dikonfigurasi) dan otomatis disertakan pada semua request trading/portfolio berikutnya. Bot akan me-refresh token secara otomatis ketika mendekati kedaluwarsa.

## Perintah Telegram yang Tersedia

- `/start` / menu utama: navigasi market, portfolio, trading, strategi, alert.
- `/help`: daftar perintah singkat.
- `/price <PAIR>`: cek harga cepat, contoh `/price BTCIDR`.
- `/trade`: alur order manual dengan inline keyboard (market/limit, konfirmasi).
- `/orders`: daftar order aktif lengkap dengan tombol cancel.
- `/portfolio`: ringkasan saldo & estimasi nilai IDR.
- `/strategy`: kelola strategi DCA/Grid/TP-SL, termasuk daftar strategi aktif.
- `/alert`: buat price alert sekali/berulang dengan konfirmasi arah.
- `/unlink`: cabut token akses saat Anda ingin menonaktifkan sesi dari perangkat tersebut.

## Pengembangan Lokal (Opsional)

Jika ingin menjalankan tanpa Docker:

```bash
poetry install
export $(cat .env | xargs)
poetry run uvicorn core.app:app --reload
```

Untuk bot & worker jalankan modul masing-masing:

```bash
poetry run python -m bot.main
poetry run python -m worker.scheduler
```

## Keamanan

- API secret disimpan dalam bentuk terenkripsi AES-256-GCM dengan key dari `APP_SECRET_KEY`.
- Nonce private API per user disimpan di Redis untuk mencegah replay.
- Rate limit dasar dapat ditambahkan via middleware pada core API.
- Token akses pengguna memiliki masa berlaku (`USER_TOKEN_TTL_SECONDS`) dan otomatis diputar ulang; gunakan `/unlink` untuk mencabut sesi secara manual bila diperlukan.
- Token akses pengguna pada bot disimpan terenkripsi (AES-GCM) menggunakan `APP_SECRET_KEY` sebelum ditulis ke Redis.
- Worker strategi memantau error; jika terjadi kegagalan beruntun, strategi dapat dihentikan manual via API.

### Endpoint Operasional

- `POST /api/auth/admin/revoke` (butuh `X-Internal-Token`): cabut token akses pengguna secara paksa tanpa menunggu pengguna menjalankan `/unlink`.

## Testing

```bash
poetry run pytest
```

## Deployment Production

- Tempatkan core API di balik reverse proxy (Nginx/Traefik) dengan TLS.
- Gunakan webhook Telegram untuk produksi (bisa diatur di bot service).
- Simpan `.env` dan secret di secrets manager (Vault, AWS Secrets Manager).
- Monitoring & logging: forward log JSON ke ELK/Graylog, tambahkan metrics (Prometheus) bila perlu.

## Lisensi

MIT.
