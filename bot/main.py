import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from bot.config import get_settings
from bot.handlers import alerts, auth, market, orders, portfolio, start, strategy, trading
from bot.services.api_client import core_api_client
from bot.services.token_store import token_store


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    redis = Redis.from_url(str(settings.redis_url))
    storage = RedisStorage(redis=redis)

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    dp.include_router(start.router)
    dp.include_router(auth.router)
    dp.include_router(market.router)
    dp.include_router(trading.router)
    dp.include_router(orders.router)
    dp.include_router(portfolio.router)
    dp.include_router(strategy.router)
    dp.include_router(alerts.router)

    async def notify(request: web.Request) -> web.Response:
        payload = await request.json()
        chat_id = payload.get("chat_id")
        text = payload.get("text")
        if not chat_id or not text:
            return web.json_response(
                {"success": False, "error": "chat_id atau text kosong"}, status=400
            )
        parse_mode = payload.get("parse_mode", "HTML")
        disable_preview = payload.get("disable_preview", True)
        await bot.send_message(
            chat_id,
            text,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_preview,
        )
        return web.json_response({"success": True})

    app = web.Application()
    app.router.add_post("/internal/notify", notify)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.bot_internal_host, settings.bot_internal_port)
    await site.start()

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await storage.close()
        await storage.wait_closed()
        await redis.close()
        await core_api_client.close()
        await token_store.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot dihentikan")
