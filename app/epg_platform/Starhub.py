from datetime import datetime, timedelta
from typing import List
from zoneinfo import ZoneInfo

from ..logger import get_logger
from ..utils import has_chinese, utc_to_utc8_datetime
from .base import BaseEPGPlatform, Channel, Program

logger = get_logger(__name__)


class StarhubPlatform(BaseEPGPlatform):
    """StarHub EPG platform implementation"""

    def __init__(self):
        super().__init__("starhub")
        self.base_url = "https://waf-starhub-metadata-api-p001.ifs.vubiquity.com/v3.1/epg"
        self.channels_url = f"{self.base_url}/channels"
        self.schedules_url = f"{self.base_url}/schedules"

    async def fetch_channels(self) -> List[Channel]:
        """Fetch channel list from StarHub API"""
        self.logger.info("Fetching channel list from StarHub")

        headers = self.get_default_headers()

        params = {
            "locale": "zh",
            "locale_default": "en_US",
            "device": "1",
            "limit": "150",
            "page": "1"
        }

        response = self.http_client.get(
            self.channels_url,
            headers=headers,
            params=params
        )

        data = response.json()
        channels = []

        for resource in data.get('resources', []):
            if resource.get('metatype') == 'Channel':
                channels.append(Channel(
                    channel_id=resource.get('id', ''),
                    name=resource.get('title', ''),
                    raw_data=resource
                ))

        self.logger.info(f"Found {len(channels)} channels from StarHub")
        return channels

    async def fetch_programs(self, channels: List[Channel]) -> List[Program]:
        """Fetch program data for all StarHub channels"""
        self.logger.info(f"Fetching program data for {len(channels)} StarHub channels")

        all_programs = []

        for channel in channels:
            try:
                programs = await self._fetch_channel_programs(channel)
                all_programs.extend(programs)
            except Exception as e:
                self.logger.error(f"Failed to fetch programs for {channel.name}: {e}")
                continue

        self.logger.info(f"Fetched {len(all_programs)} programs total")
        return all_programs

    async def _fetch_channel_programs(self, channel: Channel) -> List[Program]:
        """Fetch program data for a specific StarHub channel"""
        self.logger.debug(f"Fetching programs for channel: {channel.name} (ID: {channel.channel_id})")

        # Calculate time range (today to 6 days later)
        tz = ZoneInfo('Asia/Shanghai')
        today_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        six_days_later = today_start + timedelta(days=6)
        six_days_later_end = six_days_later.replace(hour=23, minute=59, second=59)

        today_timestamp = int(today_start.timestamp())
        six_days_later_timestamp = int(six_days_later_end.timestamp())

        headers = self.get_default_headers()

        params = {
            "locale": "zh",
            "locale_default": "en_US",
            "device": "1",
            "limit": "500",
            "page": "1",
            "in_channel_id": channel.channel_id,
            "gt_end": str(today_timestamp),      # Start time
            "lt_start": str(six_days_later_timestamp),  # End time
        }

        response = self.http_client.get(
            self.schedules_url,
            headers=headers,
            params=params
        )

        data = response.json()
        programs = []

        for resource in data.get('resources', []):
            if resource.get('metatype') == 'Schedule':
                try:
                    title = resource.get('title', '')
                    description = resource.get('description', '')
                    episode_number = resource.get('episode_number')

                    # Add episode number based on language
                    if episode_number:
                        if has_chinese(title) or has_chinese(description):
                            title += f" 第{episode_number}集"
                        else:
                            title += f" Ep{episode_number}"

                    # Convert timestamps to datetime objects
                    start_time = utc_to_utc8_datetime(resource.get('start'))
                    end_time = utc_to_utc8_datetime(resource.get('end'))

                    programs.append(Program(
                        channel_id=channel.channel_id,
                        title=title,
                        start_time=start_time,
                        end_time=end_time,
                        description=description,
                        raw_data=resource
                    ))

                except Exception as e:
                    self.logger.warning(f"Failed to parse program data: {e}")
                    continue

        self.logger.debug(f"Found {len(programs)} programs for {channel.name}")
        return programs


# Create platform instance
starhub_platform = StarhubPlatform()


# Legacy functions for backward compatibility
def request_channels():
    """Legacy function - get StarHub channel list (synchronous)"""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            logger.warning("Legacy request_channels called from async context - returning empty list")
            return []
        else:
            channels = loop.run_until_complete(starhub_platform.fetch_channels())
            # Convert to legacy format
            return [{"channelName": ch.name, "channelId": ch.channel_id} for ch in channels]
    except Exception as e:
        logger.error(f"Error in legacy request_channels: {e}")
        return []


def request_epg(channel_id, channel_name):
    """Legacy function - get EPG for specific channel (synchronous)"""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            logger.warning("Legacy request_epg called from async context - returning empty list")
            return []
        else:
            # Create a temporary channel object
            channel = Channel(channel_id=channel_id, name=channel_name)
            programs = loop.run_until_complete(starhub_platform._fetch_channel_programs(channel))

            # Convert to legacy format
            program_list = []
            for program in programs:
                program_list.append({
                    "channelName": channel_name,
                    "programName": program.title,
                    "description": program.description,
                    "start": program.start_time,
                    "end": program.end_time
                })

            return program_list
    except Exception as e:
        logger.error(f"Error in legacy request_epg: {e}")
        return []


async def get_starhub_epg():
    """Legacy function - fetch StarHub EPG data"""
    try:
        channels = await starhub_platform.fetch_channels()
        programs = await starhub_platform.fetch_programs(channels)

        # Convert to legacy format
        raw_channels = []
        raw_programs = []

        for channel in channels:
            raw_channels.append({
                "channelName": channel.name,
                "channelId": channel.channel_id
            })

        for program in programs:
            channel_name = next((ch.name for ch in channels if ch.channel_id == program.channel_id), "")
            raw_programs.append({
                "channelName": channel_name,
                "programName": program.title,
                "description": program.description,
                "start": program.start_time,
                "end": program.end_time
            })

        return raw_channels, raw_programs

    except Exception as e:
        logger.error(f"Error in legacy get_starhub_epg function: {e}", exc_info=True)
        return [], []