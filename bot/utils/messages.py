MAIN_MENU_TEXT = (
    "Selamat datang di Indodax Trading Bot!\n"
    "Pilih menu untuk melihat harga, portfolio, membuat order, atau mengatur strategi."
)

HELP_TEXT = (
    "Daftar perintah:\n"
    "/start - Tampilkan menu utama\n"
    "/help - Bantuan perintah\n"
    "/price <PAIR> - Cek harga cepat\n"
    "/trade - Buat order manual\n"
    "/orders - Lihat dan batalkan order aktif\n"
    "/portfolio - Ringkasan saldo\n"
    "/strategy - Kelola strategi otomatis\n"
    "/alert - Buat price alert\n"
    "/unlink - Cabut token akses"
)

LINK_INSTRUCTION_TEXT = (
    "Masukkan API Key Indodax Anda (tanpa teks lain).\n"
    "Setelah itu kami akan meminta API Secret secara terpisah."
)

LINK_SECRET_PROMPT = (
    "Terima kasih! Sekarang masukkan API Secret Indodax Anda."
    " Pastikan Anda berada di chat privat agar tetap aman."
)

LINK_SUCCESS_TEXT = (
    "API key berhasil terhubung! Token akses telah diperbarui secara otomatis."
)

TOKEN_MISSING_TEXT = (
    "Akun Anda belum terhubung ke Indodax."
    "\nGunakan perintah /link di chat privat untuk memasukkan API Key dan Secret."
)

TOKEN_EXPIRED_TEXT = (
    "Token akses Anda telah kedaluwarsa."
    "\nSilakan lakukan /link kembali untuk mendapatkan akses terbaru."
)

ORDER_SUMMARY_TEMPLATE = (
    "Ringkasan Order:\n"
    "Pair: {pair}\n"
    "Arah: {side}\n"
    "Tipe: {order_type}\n"
    "Jumlah: {amount}\n"
    "Harga: {price}"
)

PORTFOLIO_ROW_TEMPLATE = "{asset}: {amount:.8f} (~{value:,.0f} IDR, {pct:.2f}%)"

STRATEGY_LIST_EMPTY = "Belum ada strategi aktif untuk akun Anda."

ALERT_CREATED_TEXT = "Alert harga berhasil dibuat. Kami akan kabari saat target tercapai."
