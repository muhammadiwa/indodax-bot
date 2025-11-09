from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="📊 Market", callback_data="menu_market")],
        [InlineKeyboardButton(text="💼 Portfolio", callback_data="menu_portfolio")],
        [InlineKeyboardButton(text="💹 Trading", callback_data="menu_trading")],
        [InlineKeyboardButton(text="🤖 Strategy", callback_data="menu_strategy")],
        [InlineKeyboardButton(text="🔔 Alerts", callback_data="menu_alerts")],
        [InlineKeyboardButton(text="⚙️ Pengaturan API", callback_data="menu_api")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def market_pairs_keyboard(pairs: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for pair in pairs:
        rows.append([
            InlineKeyboardButton(text=pair.upper(), callback_data=f"market:pair:{pair.upper()}"),
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Kembali", callback_data="menu_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def alert_pairs_keyboard(pairs: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for pair in pairs:
        rows.append([
            InlineKeyboardButton(text=pair.upper(), callback_data=f"alert:pair:{pair.upper()}"),
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Menu", callback_data="menu_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def trade_pairs_keyboard(pairs: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for pair in pairs:
        rows.append([
            InlineKeyboardButton(text=pair.upper(), callback_data=f"trade:pair:{pair.upper()}"),
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Menu", callback_data="menu_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def trading_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Order Manual", callback_data="trade:start")],
            [InlineKeyboardButton(text="📄 Order Aktif", callback_data="orders:list")],
            [InlineKeyboardButton(text="⬅️ Menu", callback_data="menu_home")],
        ]
    )


def trade_side_keyboard(pair: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Beli", callback_data=f"trade:side:{pair}:buy"),
                InlineKeyboardButton(text="🔴 Jual", callback_data=f"trade:side:{pair}:sell"),
            ],
            [InlineKeyboardButton(text="⬅️ Pilih Pair", callback_data="trade:back:pairs")],
        ]
    )


def trade_type_keyboard(pair: str, side: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Market", callback_data=f"trade:type:{pair}:{side}:market"
                ),
                InlineKeyboardButton(
                    text="Limit", callback_data=f"trade:type:{pair}:{side}:limit"
                ),
            ],
            [InlineKeyboardButton(text="⬅️ Pilih Arah", callback_data=f"trade:pair:{pair}")],
        ]
    )


def trade_amount_keyboard(pair: str, side: str, order_type: str) -> InlineKeyboardMarkup:
    amounts = [100000, 250000, 500000]
    rows = [
        [
            InlineKeyboardButton(
                text=f"{amount:,} IDR",
                callback_data=f"trade:amount:{pair}:{side}:{order_type}:idr:{amount}",
            )
            for amount in amounts
        ],
        [
            InlineKeyboardButton(
                text="Ketik jumlah coin",
                callback_data=f"trade:amount:{pair}:{side}:{order_type}:coin:manual",
            )
        ],
        [InlineKeyboardButton(text="⬅️ Pilih Tipe", callback_data=f"trade:type:{pair}:{side}:back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def trade_price_keyboard(pair: str, side: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Gunakan harga saat ini",
                    callback_data=f"trade:price:{pair}:{side}:current",
                )
            ],
            [InlineKeyboardButton(text="⬅️ Pilih Tipe", callback_data=f"trade:type:{pair}:{side}:limit")],
        ]
    )


def confirmation_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Konfirmasi", callback_data="trade:confirm"),
            InlineKeyboardButton(text="❌ Batal", callback_data="trade:cancel"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def orders_keyboard(order_id: int, telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Batalkan",
                    callback_data=f"orders:cancel:{order_id}:{telegram_id}",
                )
            ]
        ]
    )


def orders_list_keyboard(order_ids: list[int], telegram_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"Batalkan #{order_id}",
                callback_data=f"orders:cancel:{order_id}:{telegram_id}",
            )
        ]
        for order_id in order_ids
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Trading", callback_data="menu_trading")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def orders_confirm_keyboard(order_id: int, telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Ya, batalkan",
                    callback_data=f"orders:confirm:{order_id}:{telegram_id}",
                ),
                InlineKeyboardButton(
                    text="Tidak", callback_data="orders:cancelled"
                ),
            ]
        ]
    )


def strategy_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ DCA", callback_data="strategy:create:dca")],
            [InlineKeyboardButton(text="➕ Grid", callback_data="strategy:create:grid")],
            [InlineKeyboardButton(text="➕ TP/SL", callback_data="strategy:create:tp_sl")],
            [InlineKeyboardButton(text="📋 Strategi Aktif", callback_data="strategy:list")],
            [InlineKeyboardButton(text="⬅️ Menu", callback_data="menu_home")],
        ]
    )


def strategy_pairs_keyboard(pairs: list[str], mode: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=pair.upper(), callback_data=f"strategy:pair:{mode}:{pair.upper()}"
            )
        ]
        for pair in pairs
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Kembali", callback_data="strategy:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def strategy_interval_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Harian", callback_data="strategy:dca:interval:daily")],
            [InlineKeyboardButton(text="Mingguan", callback_data="strategy:dca:interval:weekly")],
            [InlineKeyboardButton(text="Per Jam", callback_data="strategy:dca:interval:hourly")],
        ]
    )


def alerts_direction_keyboard(pair: str, target: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Naik ≥", callback_data=f"alert:direction:{pair}:{target}:up"
                ),
                InlineKeyboardButton(
                    text="Turun ≤", callback_data=f"alert:direction:{pair}:{target}:down"
                ),
            ]
        ]
    )


def alerts_repeat_keyboard(pair: str, target: float, direction: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Sekali", callback_data=f"alert:repeat:{pair}:{target}:{direction}:0"
                ),
                InlineKeyboardButton(
                    text="Berulang", callback_data=f"alert:repeat:{pair}:{target}:{direction}:1"
                ),
            ]
        ]
    )
