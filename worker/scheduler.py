import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from worker.config import get_settings
from worker.price_feed import price_feed
from worker.tasks.alerts import check_price_alerts
from worker.tasks.dca import run_dca_strategies
from worker.tasks.grid import run_grid_strategies
from worker.tasks.orders import monitor_orders
from worker.tasks.tp_sl import monitor_tp_sl
from worker.clients.core_api import core_api_client


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
    scheduler.add_job(run_dca_strategies, IntervalTrigger(minutes=1))
    scheduler.add_job(run_grid_strategies, IntervalTrigger(minutes=5))
    scheduler.add_job(monitor_tp_sl, IntervalTrigger(minutes=1))
    scheduler.add_job(check_price_alerts, IntervalTrigger(seconds=settings.worker_poll_interval_seconds))
    scheduler.add_job(monitor_orders, IntervalTrigger(minutes=1))

    await price_feed.start()
    scheduler.start()
    logging.info("Worker scheduler berjalan")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Worker dihentikan")
    finally:
        scheduler.shutdown()
        await price_feed.stop()
        await core_api_client.close()


if __name__ == "__main__":
    asyncio.run(main())
