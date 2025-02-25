from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.epg_platform import MyTvSuper


class MyTvSuperScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    async def fetch_channels(self):
        # Assuming MyTvSuper has been properly defined and imported
        logger.info("Fetching channels from MyTvSuper...")
        try:
            await MyTvSuper.get_channels()
            logger.info(f"Fetched MyTvSuper: Success")
        except Exception as e:
            logger.error(f"Error fetching channels: {e}")

    def start(self):
        # Schedule the `fetch_channels` method to run every 12 hours
        trigger = IntervalTrigger(hours=12)
        self.scheduler.add_job(self.fetch_channels, trigger)
        self.scheduler.start()
        logger.info("Scheduler started, will fetch channels every 12 hours.")
