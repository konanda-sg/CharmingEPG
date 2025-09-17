# Template for refactoring platform modules to new architecture
# This shows the pattern for converting old platform modules

from typing import List
from datetime import datetime

from ..logger import get_logger
from .base import BaseEPGPlatform, Channel, Program

logger = get_logger(__name__)


class TemplatePlatform(BaseEPGPlatform):
    """Template EPG platform implementation"""

    def __init__(self):
        super().__init__("template")  # Replace with actual platform name
        self.base_url = "https://api.example.com"  # Replace with actual API URL

    async def fetch_channels(self) -> List[Channel]:
        """Fetch channel list from platform API"""
        self.logger.info("Fetching channel list from Template Platform")

        headers = self.get_default_headers({
            # Add platform-specific headers here
        })

        # Make API call to fetch channels
        response = self.http_client.get(
            f"{self.base_url}/channels",  # Replace with actual endpoint
            headers=headers
        )

        data = response.json()
        channels = []

        # Parse response and create Channel objects
        for channel_data in data.get('channels', []):  # Adjust based on response structure
            channels.append(Channel(
                channel_id=channel_data.get('id', ''),
                name=channel_data.get('name', ''),
                # Add other channel properties as needed
                raw_data=channel_data
            ))

        self.logger.info(f"Found {len(channels)} channels from Template Platform")
        return channels

    async def fetch_programs(self, channels: List[Channel]) -> List[Program]:
        """Fetch program data for all channels"""
        self.logger.info(f"Fetching program data for {len(channels)} channels")

        all_programs = []
        for channel in channels:
            try:
                programs = await self._fetch_channel_programs(channel)
                all_programs.extend(programs)
            except Exception as e:
                self.logger.error(f"Failed to fetch programs for channel {channel.name}: {e}")
                continue

        self.logger.info(f"Fetched {len(all_programs)} programs total")
        return all_programs

    async def _fetch_channel_programs(self, channel: Channel) -> List[Program]:
        """Fetch program data for a specific channel"""
        self.logger.debug(f"Fetching programs for channel: {channel.name}")

        headers = self.get_default_headers()

        # Make API call to fetch programs for this channel
        response = self.http_client.get(
            f"{self.base_url}/programs/{channel.channel_id}",  # Replace with actual endpoint
            headers=headers
        )

        data = response.json()
        programs = []

        # Parse response and create Program objects
        for program_data in data.get('programs', []):  # Adjust based on response structure
            try:
                # Parse time data (adjust format as needed)
                start_time = self._parse_time(program_data.get('start_time'))
                end_time = self._parse_time(program_data.get('end_time'))

                programs.append(Program(
                    channel_id=channel.channel_id,
                    title=program_data.get('title', ''),
                    start_time=start_time,
                    end_time=end_time,
                    description=program_data.get('description', ''),
                    raw_data=program_data
                ))

            except Exception as e:
                self.logger.warning(f"Failed to parse program data: {e}")
                continue

        self.logger.debug(f"Found {len(programs)} programs for {channel.name}")
        return programs

    def _parse_time(self, time_str: str) -> datetime:
        """Parse time string to datetime object (customize based on platform format)"""
        # This is a placeholder - adjust the parsing logic for each platform
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except:
            return datetime.now()


# Create platform instance
template_platform = TemplatePlatform()


# Legacy functions for backward compatibility (customize as needed)
async def legacy_function_name():
    """Legacy function - maintain backward compatibility"""
    try:
        channels = await template_platform.fetch_channels()
        programs = await template_platform.fetch_programs(channels)

        # Convert to legacy format if needed
        # Return in the format expected by existing code

        return channels, programs
    except Exception as e:
        logger.error(f"Error in legacy function: {e}", exc_info=True)
        return [], []