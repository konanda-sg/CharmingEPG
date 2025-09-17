import asyncio
from datetime import datetime
from typing import List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Query

from .config import Config
from .logger import get_logger
from .file_manager import EPGFileManager
from .epg_platform import MyTvSuper, Hami
from .epg_platform.Astro import get_astro_epg
from .epg_platform.CN_epg_pw import get_cn_channels_epg
from .epg_platform.HOY import get_hoy_epg
from .epg_platform.NowTV import request_nowtv_today_epg
from .epg_platform.RTHK import get_rthk_epg
from .epg_platform.Starhub import get_starhub_epg

logger = get_logger(__name__)

app = FastAPI(
    title=Config.APP_NAME,
    version=Config.APP_VERSION,
    description="Electronic Program Guide (EPG) aggregation service for Asian streaming platforms",
    openapi_url=None
)


@app.get("/")
async def root():
    """Health check endpoint"""
    enabled_platforms = [p["platform"] for p in Config.get_enabled_platforms()]
    return {
        "service": Config.APP_NAME,
        "version": Config.APP_VERSION,
        "status": "healthy",
        "enabled_platforms": enabled_platforms,
        "update_interval_minutes": Config.EPG_UPDATE_INTERVAL
    }


# Create scheduler instance
scheduler = AsyncIOScheduler()


@scheduler.scheduled_job('interval', minutes=Config.EPG_UPDATE_INTERVAL)
async def scheduled_epg_update():
    """Scheduled task to update EPG data from all enabled platforms"""
    logger.info(f"Starting scheduled EPG update at {datetime.now()}")
    await update_all_enabled_platforms()


async def request_my_tv_super_epg():
    """Update MyTV Super EPG data"""
    platform = "tvb"
    logger.info(f"Updating EPG for platform: {platform}")

    try:
        if EPGFileManager.read_epg_file(platform) is not None:
            logger.info(f"Today's EPG already exists for {platform}, skipping update")
            return

        channels, programs = await MyTvSuper.get_channels(force=True)
        if not channels:
            logger.warning(f"No channels found for {platform}")
            return

        response_xml = await gen_channel(channels, programs)

        if EPGFileManager.save_epg_file(platform, response_xml):
            EPGFileManager.delete_old_epg_files(platform)
            logger.info(f"Successfully updated EPG for {platform}")
        else:
            logger.error(f"Failed to save EPG file for {platform}")

    except Exception as e:
        logger.error(f"Error updating EPG for {platform}: {e}", exc_info=True)


async def request_hami_epg():
    """Update Hami EPG data"""
    platform = "hami"
    logger.info(f"Updating EPG for platform: {platform}")

    try:
        if EPGFileManager.read_epg_file(platform) is not None:
            logger.info(f"Today's EPG already exists for {platform}, skipping update")
            return

        channels, programs = await Hami.request_all_epg()
        if not channels:
            logger.warning(f"No channels found for {platform}")
            return

        response_xml = await gen_channel(channels, programs)

        if EPGFileManager.save_epg_file(platform, response_xml):
            EPGFileManager.delete_old_epg_files(platform)
            logger.info(f"Successfully updated EPG for {platform}")
        else:
            logger.error(f"Failed to save EPG file for {platform}")

    except Exception as e:
        logger.error(f"Error updating EPG for {platform}: {e}", exc_info=True)


async def request_cn_epg():
    """Update CN (epg.pw) EPG data"""
    platform = "cn"
    logger.info(f"Updating EPG for platform: {platform}")

    try:
        if EPGFileManager.read_epg_file(platform) is not None:
            logger.info(f"Today's EPG already exists for {platform}, skipping update")
            return

        response_xml = await get_cn_channels_epg()
        if not response_xml:
            logger.warning(f"No EPG data received for {platform}")
            return

        # Convert string to bytes for consistent handling
        xml_bytes = response_xml.encode('utf-8') if isinstance(response_xml, str) else response_xml

        if EPGFileManager.save_epg_file(platform, xml_bytes):
            EPGFileManager.delete_old_epg_files(platform)
            logger.info(f"Successfully updated EPG for {platform}")
        else:
            logger.error(f"Failed to save EPG file for {platform}")

    except Exception as e:
        logger.error(f"Error updating EPG for {platform}: {e}", exc_info=True)


async def request_astro_epg():
    """Update Astro Go EPG data"""
    platform = "astro"
    logger.info(f"Updating EPG for platform: {platform}")

    try:
        if EPGFileManager.read_epg_file(platform) is not None:
            logger.info(f"Today's EPG already exists for {platform}, skipping update")
            return

        channels, programs = await get_astro_epg()
        if not channels:
            logger.warning(f"No channels found for {platform}")
            return

        response_xml = await gen_channel(channels, programs)

        if EPGFileManager.save_epg_file(platform, response_xml):
            EPGFileManager.delete_old_epg_files(platform)
            logger.info(f"Successfully updated EPG for {platform}")
        else:
            logger.error(f"Failed to save EPG file for {platform}")

    except Exception as e:
        logger.error(f"Error updating EPG for {platform}: {e}", exc_info=True)


async def request_rthk_epg():
    """Update RTHK EPG data"""
    platform = "rthk"
    logger.info(f"Updating EPG for platform: {platform}")

    try:
        if EPGFileManager.read_epg_file(platform) is not None:
            logger.info(f"Today's EPG already exists for {platform}, skipping update")
            return

        channels, programs = await get_rthk_epg()
        if not channels:
            logger.warning(f"No channels found for {platform}")
            return

        response_xml = await gen_channel(channels, programs)

        if EPGFileManager.save_epg_file(platform, response_xml):
            EPGFileManager.delete_old_epg_files(platform)
            logger.info(f"Successfully updated EPG for {platform}")
        else:
            logger.error(f"Failed to save EPG file for {platform}")

    except Exception as e:
        logger.error(f"Error updating EPG for {platform}: {e}", exc_info=True)


async def request_hoy_epg():
    """Update HOY EPG data"""
    platform = "hoy"
    logger.info(f"Updating EPG for platform: {platform}")

    try:
        if EPGFileManager.read_epg_file(platform) is not None:
            logger.info(f"Today's EPG already exists for {platform}, skipping update")
            return

        channels, programs = await get_hoy_epg()
        if not channels:
            logger.warning(f"No channels found for {platform}")
            return

        response_xml = await gen_channel(channels, programs)

        if EPGFileManager.save_epg_file(platform, response_xml):
            EPGFileManager.delete_old_epg_files(platform)
            logger.info(f"Successfully updated EPG for {platform}")
        else:
            logger.error(f"Failed to save EPG file for {platform}")

    except Exception as e:
        logger.error(f"Error updating EPG for {platform}: {e}", exc_info=True)


async def request_now_tv_epg():
    """Update NowTV EPG data"""
    platform = "nowtv"
    logger.info(f"Updating EPG for platform: {platform}")

    try:
        if EPGFileManager.read_epg_file(platform) is not None:
            logger.info(f"Today's EPG already exists for {platform}, skipping update")
            return

        response_xml = await request_nowtv_today_epg()
        if not response_xml:
            logger.warning(f"No EPG data received for {platform}")
            return

        if EPGFileManager.save_epg_file(platform, response_xml):
            EPGFileManager.delete_old_epg_files(platform)
            logger.info(f"Successfully updated EPG for {platform}")
        else:
            logger.error(f"Failed to save EPG file for {platform}")

    except Exception as e:
        logger.error(f"Error updating EPG for {platform}: {e}", exc_info=True)


async def request_starhub_epg():
    """Update StarHub EPG data"""
    platform = "starhub"
    logger.info(f"Updating EPG for platform: {platform}")

    try:
        if EPGFileManager.read_epg_file(platform) is not None:
            logger.info(f"Today's EPG already exists for {platform}, skipping update")
            return

        channels, programs = await get_starhub_epg()
        if not channels:
            logger.warning(f"No channels found for {platform}")
            return

        response_xml = await gen_channel(channels, programs)

        if EPGFileManager.save_epg_file(platform, response_xml):
            EPGFileManager.delete_old_epg_files(platform)
            logger.info(f"Successfully updated EPG for {platform}")
        else:
            logger.error(f"Failed to save EPG file for {platform}")

    except Exception as e:
        logger.error(f"Error updating EPG for {platform}: {e}", exc_info=True)


@app.get("/epg/{platform}")
async def get_platform_epg(platform: str):
    """Get EPG data for a specific platform"""
    logger.info(f"Serving EPG data for platform: {platform}")
    return EPGFileManager.get_single_platform_epg(platform)


@app.get("/epg")
async def get_custom_aggregate_epg(platforms: str = Query(..., description="Comma-separated platform list in priority order")):
    """
    Get aggregated EPG data from custom platform selection

    Example: ?platforms=tvb,nowtv,hami
    """
    platform_list = [p.strip() for p in platforms.split(',') if p.strip()]
    logger.info(f"Serving custom aggregated EPG for platforms: {platform_list}")
    return EPGFileManager.aggregate_epg_files(platform_list)


@app.get("/all")
async def get_all_enabled_platforms_epg():
    """Get aggregated EPG data from all enabled platforms"""
    enabled_platforms = [p["platform"] for p in Config.get_enabled_platforms()]
    logger.info(f"Serving aggregated EPG for all enabled platforms: {enabled_platforms}")
    return EPGFileManager.aggregate_epg_files(enabled_platforms)


async def gen_channel(channels, programs):
    """Generate EPG XML from channels and programs data"""
    from .epg.EpgGenerator import generateEpg
    return await generateEpg(channels, programs)


async def update_all_enabled_platforms():
    """Update EPG data for all enabled platforms"""
    enabled_platforms = Config.get_enabled_platforms()

    if not enabled_platforms:
        logger.warning("No platforms are enabled")
        return

    logger.info(f"Starting EPG update for {len(enabled_platforms)} enabled platforms")

    tasks = [
        globals()[conf["fetcher"]]()
        for conf in enabled_platforms
    ]

    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and log any exceptions
    success_count = 0
    error_count = 0

    for i, result in enumerate(results):
        platform_config = enabled_platforms[i]
        platform_name = platform_config["name"]

        if isinstance(result, Exception):
            error_count += 1
            logger.error(f"Failed to update EPG for {platform_name}: {result}", exc_info=True)
        else:
            success_count += 1
            logger.debug(f"Successfully updated EPG for {platform_name}")

    logger.info(f"EPG update completed: {success_count} successful, {error_count} failed")


@app.on_event("startup")
async def startup():
    """Application startup event"""
    logger.info(f"Starting {Config.APP_NAME} v{Config.APP_VERSION}")
    logger.info(f"EPG update interval: {Config.EPG_UPDATE_INTERVAL} minutes")

    enabled_platforms = [p["name"] for p in Config.get_enabled_platforms()]
    logger.info(f"Enabled platforms: {', '.join(enabled_platforms)}")

    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started")

    # Trigger initial EPG update
    asyncio.create_task(update_all_enabled_platforms())
    logger.info("Initial EPG update triggered")