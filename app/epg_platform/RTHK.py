import pytz
from datetime import datetime, timedelta
from typing import List
from bs4 import BeautifulSoup

from ..logger import get_logger
from .base import BaseEPGPlatform, Channel, Program

logger = get_logger(__name__)


class RTHKPlatform(BaseEPGPlatform):
    """RTHK EPG platform implementation"""

    def __init__(self):
        super().__init__("rthk")
        self.base_url = "https://www.rthk.hk/timetable"

        # RTHK channel definitions
        self.channel_definitions = [
            {"channelName": "RTHK31", "channelId": "tv31"},
            {"channelName": "RTHK32", "channelId": "tv32"},
            {"channelName": "RTHK33", "channelId": "tv33"},
            {"channelName": "RTHK34", "channelId": "tv34"},
            {"channelName": "RTHK35", "channelId": "tv35"},
        ]

    async def fetch_channels(self) -> List[Channel]:
        """Fetch channel list from RTHK (predefined channels)"""
        self.logger.info("Creating RTHK channel list")

        channels = []
        for channel_def in self.channel_definitions:
            channels.append(Channel(
                channel_id=channel_def["channelId"],
                name=channel_def["channelName"],
                raw_data=channel_def
            ))

        self.logger.info(f"Found {len(channels)} RTHK channels")
        return channels

    async def fetch_programs(self, channels: List[Channel]) -> List[Program]:
        """Fetch program data for all RTHK channels"""
        self.logger.info(f"Fetching program data for {len(channels)} RTHK channels")

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
        """Fetch program data for a specific RTHK channel"""
        self.logger.debug(f"Fetching programs for channel: {channel.name}")

        url = f"{self.base_url}/{channel.channel_id}"

        response = self.http_client.get(url)

        programs = self._parse_epg_from_html(response.text, channel)

        self.logger.debug(f"Found {len(programs)} programs for {channel.name}")
        return programs

    def _parse_epg_from_html(self, html_content: str, channel: Channel) -> List[Program]:
        """Parse EPG data from RTHK HTML page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        programs = []

        # Today's date for filtering
        today = datetime.now().strftime("%Y%m%d")

        # Find all date blocks
        date_blocks = soup.find_all('div', class_='slideBlock')

        for block in date_blocks:
            date_str = block.get('date')

            # Only process today and future dates
            if date_str and date_str >= today:
                try:
                    # Parse date
                    year = int(date_str[0:4])
                    month = int(date_str[4:6])
                    day = int(date_str[6:8])

                    # Find all programs for this date
                    program_blocks = block.find_all('div', class_='shdBlock')

                    for program_block in program_blocks:
                        try:
                            program = self._parse_program_block(program_block, year, month, day, channel)
                            if program:
                                programs.append(program)
                        except Exception as e:
                            self.logger.warning(f"Failed to parse program block: {e}")
                            continue

                except Exception as e:
                    self.logger.warning(f"Failed to parse date block for {date_str}: {e}")
                    continue

        return programs

    def _parse_program_block(self, program_block, year: int, month: int, day: int, channel: Channel) -> Program:
        """Parse a single program block from HTML"""
        # Get time information
        time_block = program_block.find('div', class_='shTimeBlock')
        if not time_block:
            return None

        time_elements = time_block.find_all('p', class_='timeDis')
        if not time_elements:
            return None

        start_time_str = time_elements[0].text.strip()
        end_time_str = time_elements[2].text.strip() if len(time_elements) > 2 else None

        # Parse start time
        try:
            start_hour, start_min = map(int, start_time_str.split(':'))
            start_datetime = datetime(year, month, day, start_hour, start_min)
            start_datetime = pytz.timezone('Asia/Shanghai').localize(start_datetime)
        except:
            return None

        # Parse end time
        if end_time_str:
            try:
                end_hour, end_min = map(int, end_time_str.split(':'))
                end_datetime = datetime(year, month, day, end_hour, end_min)

                # Handle day crossing
                if end_hour < start_hour or (end_hour == start_hour and end_min < start_min):
                    end_datetime += timedelta(days=1)

                end_datetime = pytz.timezone('Asia/Shanghai').localize(end_datetime)
            except:
                end_datetime = start_datetime + timedelta(minutes=30)
        else:
            # Default to 30 minutes if no end time
            end_datetime = start_datetime + timedelta(minutes=30)

        # Get program title
        title_block = program_block.find('div', class_='shTitle')
        if not title_block or not title_block.find('a'):
            return None

        program_name = title_block.find('a').text.strip()

        # Get program description
        sub_title_block = program_block.find('div', class_='shSubTitle')
        description = ""
        if sub_title_block and sub_title_block.find('a'):
            description = sub_title_block.find('a').text.strip()

        return Program(
            channel_id=channel.channel_id,
            title=program_name,
            start_time=start_datetime,
            end_time=end_datetime,
            description=description,
            raw_data={
                'date': f"{year:04d}{month:02d}{day:02d}",
                'start_time_str': start_time_str,
                'end_time_str': end_time_str
            }
        )


# Create platform instance
rthk_platform = RTHKPlatform()


# Legacy functions for backward compatibility
rthk_channels = [
    {"channelName": "RTHK31", "channelId": "tv31"},
    {"channelName": "RTHK32", "channelId": "tv32"},
    {"channelName": "RTHK33", "channelId": "tv33"},
    {"channelName": "RTHK34", "channelId": "tv34"},
    {"channelName": "RTHK35", "channelId": "tv35"},
]


def parse_epg_from_html(html_content, channel_name):
    """Legacy function - parse EPG from HTML"""
    try:
        # Create a temporary channel object
        channel = Channel(channel_id="temp", name=channel_name)
        programs = rthk_platform._parse_epg_from_html(html_content, channel)

        # Convert to legacy format
        results = []
        for program in programs:
            results.append({
                "channelName": channel_name,
                "programName": program.title,
                "description": program.description,
                "start": program.start_time,
                "end": program.end_time
            })

        return results
    except Exception as e:
        logger.error(f"Error in legacy parse_epg_from_html: {e}")
        return []


async def get_rthk_epg():
    """Legacy function - fetch RTHK EPG data"""
    try:
        channels = await rthk_platform.fetch_channels()
        programs = await rthk_platform.fetch_programs(channels)

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
        logger.error(f"Error in legacy get_rthk_epg function: {e}", exc_info=True)
        return [], []