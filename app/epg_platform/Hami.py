import pytz
from datetime import datetime, timedelta
from typing import List

from ..logger import get_logger
from .base import BaseEPGPlatform, Channel, Program

logger = get_logger(__name__)


class HamiPlatform(BaseEPGPlatform):
    """Hami Video EPG platform implementation"""

    def __init__(self):
        super().__init__("hami")
        self.base_url = "https://apl-hamivideo.cdn.hinet.net/HamiVideo"
        self.user_agent = "HamiVideo/7.12.806(Android 11;GM1910) OKHTTP/3.12.2"

    def get_platform_headers(self):
        """Get Hami-specific headers"""
        return {
            'X-ClientSupport-UserProfile': '1',
            'User-Agent': self.user_agent
        }

    async def fetch_channels(self) -> List[Channel]:
        """Fetch channel list from Hami Video API"""
        self.logger.info("Fetching channel list from Hami Video")

        params = {
            "appVersion": "7.12.806",
            "deviceType": "1",
            "appOS": "android",
            "menuId": "162"
        }

        response = self.http_client.get(
            f"{self.base_url}/getUILayoutById.php",
            headers=self.get_platform_headers(),
            params=params
        )

        data = response.json()
        channels = []

        # Find the channel list category
        elements = []
        for info in data.get("UIInfo", []):
            if info.get("title") == "頻道一覽":
                elements = info.get('elements', [])
                break

        for element in elements:
            if element.get('title') and element.get('contentPk'):
                channels.append(Channel(
                    channel_id=element['contentPk'],
                    name=element['title'],
                    content_pk=element['contentPk'],
                    raw_data=element
                ))

        self.logger.info(f"Found {len(channels)} channels from Hami Video")
        return channels

    async def fetch_programs(self, channels: List[Channel]) -> List[Program]:
        """Fetch program data for all channels"""
        self.logger.info(f"Fetching program data for {len(channels)} channels")

        all_programs = []
        for channel in channels:
            try:
                programs = await self._fetch_channel_programs(
                    channel.name,
                    channel.extra_data.get('content_pk')
                )
                all_programs.extend(programs)
            except Exception as e:
                self.logger.error(f"Failed to fetch programs for channel {channel.name}: {e}")
                continue

        self.logger.info(f"Fetched {len(all_programs)} programs total")
        return all_programs

    async def _fetch_channel_programs(self, channel_name: str, content_pk: str) -> List[Program]:
        """Fetch program data for a specific channel"""
        self.logger.debug(f"Fetching programs for channel: {channel_name}")

        programs = []

        # Fetch EPG data for 7 days
        for i in range(7):
            try:
                date = datetime.now() + timedelta(days=i)
                formatted_date = date.strftime('%Y-%m-%d')

                params = {
                    "deviceType": "1",
                    "Date": formatted_date,
                    "contentPk": content_pk,
                }

                response = self.http_client.get(
                    f"{self.base_url}/getEpgByContentIdAndDate.php",
                    headers=self.get_platform_headers(),
                    params=params
                )

                data = response.json()
                ui_info = data.get('UIInfo', [])

                if ui_info and len(ui_info) > 0:
                    elements = ui_info[0].get('elements', [])

                    for element in elements:
                        program_info_list = element.get('programInfo', [])
                        if program_info_list:
                            program_info = program_info_list[0]
                            hint_se = program_info.get('hintSE')

                            if hint_se:
                                try:
                                    start_time, end_time = self._parse_hami_time(hint_se)

                                    programs.append(Program(
                                        channel_id=content_pk,
                                        title=program_info.get('programName', ''),
                                        start_time=start_time,
                                        end_time=end_time,
                                        description="",
                                        raw_data=program_info
                                    ))
                                except Exception as e:
                                    self.logger.warning(f"Failed to parse program time: {e}")
                                    continue

            except Exception as e:
                self.logger.warning(f"Failed to fetch EPG for {channel_name} on day {i}: {e}")
                continue

        self.logger.debug(f"Found {len(programs)} programs for {channel_name}")
        return programs

    def _parse_hami_time(self, time_range: str):
        """Parse Hami time range string to datetime objects"""
        start_time_str, end_time_str = time_range.split('~')

        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")

        # Add Shanghai timezone
        shanghai_tz = pytz.timezone('Asia/Shanghai')
        start_time_shanghai = shanghai_tz.localize(start_time)
        end_time_shanghai = shanghai_tz.localize(end_time)

        return start_time_shanghai, end_time_shanghai


# Create platform instance
hami_platform = HamiPlatform()


# Legacy functions for backward compatibility
async def request_channel_list():
    """Legacy function - fetch channel list"""
    try:
        channels = await hami_platform.fetch_channels()
        return [{"channelName": ch.name, "contentPk": ch.channel_id} for ch in channels]
    except Exception as e:
        logger.error(f"Error in legacy request_channel_list function: {e}", exc_info=True)
        return []


async def get_programs_with_retry(channel):
    """Legacy function with retry logic - now handled by http_client"""
    try:
        programs = await request_epg(channel['channelName'], channel['contentPk'])
        return programs
    except Exception as e:
        logger.error(f"Error requesting EPG for {channel['channelName']}: {e}")
        return []


async def request_all_epg():
    """Legacy function - fetch all EPG data"""
    try:
        channels = await hami_platform.fetch_channels()
        programs = await hami_platform.fetch_programs(channels)

        # Convert to legacy format
        raw_channels = [{"channelName": ch.name} for ch in channels]
        raw_programs = []

        for program in programs:
            raw_programs.append({
                "channelName": next((ch.name for ch in channels if ch.channel_id == program.channel_id), ""),
                "programName": program.title,
                "description": program.description,
                "start": program.start_time,
                "end": program.end_time
            })

        return raw_channels, raw_programs

    except Exception as e:
        logger.error(f"Error in legacy request_all_epg function: {e}", exc_info=True)
        return [], []


async def request_epg(channel_name: str, content_pk: str):
    """Legacy function - fetch EPG for specific channel"""
    try:
        programs = await hami_platform._fetch_channel_programs(channel_name, content_pk)

        # Convert to legacy format
        result = []
        for program in programs:
            result.append({
                "channelName": channel_name,
                "programName": program.title,
                "description": program.description,
                "start": program.start_time,
                "end": program.end_time
            })

        return result
    except Exception as e:
        logger.error(f"Error in legacy request_epg function: {e}", exc_info=True)
        return []


def hami_time_to_datetime(time_range: str):
    """Legacy utility function"""
    return hami_platform._parse_hami_time(time_range)