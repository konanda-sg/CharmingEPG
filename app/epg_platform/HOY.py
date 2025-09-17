import xml.etree.ElementTree as ET
import pytz
from datetime import datetime
from typing import List

from ..logger import get_logger
from .base import BaseEPGPlatform, Channel, Program

logger = get_logger(__name__)


class HOYPlatform(BaseEPGPlatform):
    """HOY TV EPG platform implementation"""

    def __init__(self):
        super().__init__("hoy")
        self.channel_list_url = "https://api2.hoy.tv/api/v3/a/channel"

    async def fetch_channels(self) -> List[Channel]:
        """Fetch channel list from HOY TV API"""
        self.logger.info("📡 正在从 HOY TV 获取频道列表")

        response = self.http_client.get(self.channel_list_url)
        data = response.json()

        channels = []

        if data.get('code') == 200:
            for raw_channel in data.get('data', []):
                name_info = raw_channel.get('name', {})
                channel_name = name_info.get('zh_hk', name_info.get('en', 'Unknown'))

                epg_url = raw_channel.get('epg')
                logo = raw_channel.get('image')

                if channel_name and epg_url:
                    channels.append(Channel(
                        channel_id=str(raw_channel.get('id', '')),
                        name=channel_name,
                        epg_url=epg_url,
                        logo=logo,
                        raw_data=raw_channel
                    ))

        self.logger.info(f"📺 从 HOY TV 发现 {len(channels)} 个频道")
        return channels

    async def fetch_programs(self, channels: List[Channel]) -> List[Program]:
        """Fetch program data for all HOY TV channels"""
        self.logger.info(f"📡 正在抓取 {len(channels)} 个 HOY TV 频道的节目数据")

        all_programs = []

        for channel in channels:
            try:
                programs = await self._fetch_channel_programs(channel)
                all_programs.extend(programs)
            except Exception as e:
                self.logger.error(f"❌ 获取频道 {channel.name} 节目数据失败: {e}")
                continue

        self.logger.info(f"📊 总共抓取了 {len(all_programs)} 个节目")
        return all_programs

    async def _fetch_channel_programs(self, channel: Channel) -> List[Program]:
        """Fetch program data for a specific HOY TV channel"""
        self.logger.debug(f"🔍 正在获取频道节目: {channel.name}")

        epg_url = channel.extra_data.get('epg_url')
        if not epg_url:
            self.logger.warning(f"⚠️ 频道 {channel.name} 未找到 EPG URL")
            return []

        response = self.http_client.get(epg_url)

        programs = self._parse_epg_xml(response.text, channel)

        self.logger.debug(f"📺 在 {channel.name} 中发现 {len(programs)} 个节目")
        return programs

    def _parse_epg_xml(self, xml_content: str, channel: Channel) -> List[Program]:
        """Parse EPG XML content for HOY TV"""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            self.logger.error(f"❌ 解析 {channel.name} 的 XML 失败: {e}")
            return []

        programs = []
        shanghai_tz = pytz.timezone('Asia/Shanghai')
        today = datetime.now(shanghai_tz).replace(hour=0, minute=0, second=0, microsecond=0)

        for channel_elem in root.findall('./Channel'):
            for epg_item in channel_elem.findall('./EpgItem'):
                try:
                    # Parse time strings
                    start_time_elem = epg_item.find('./EpgStartDateTime')
                    end_time_elem = epg_item.find('./EpgEndDateTime')

                    if start_time_elem is None or end_time_elem is None:
                        continue

                    start_time_str = start_time_elem.text
                    end_time_str = end_time_elem.text

                    # Parse and localize times
                    start_time = shanghai_tz.localize(datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S"))
                    end_time = shanghai_tz.localize(datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S"))

                    # Only include programs from today onwards
                    if start_time.date() >= today.date():
                        # Get episode information
                        episode_info = epg_item.find('./EpisodeInfo')
                        if episode_info is not None:
                            short_desc_elem = episode_info.find('./EpisodeShortDescription')
                            episode_index_elem = episode_info.find('./EpisodeIndex')

                            short_desc = short_desc_elem.text if short_desc_elem is not None else ""
                            episode_index = episode_index_elem.text if episode_index_elem is not None else "0"

                            # Build program name
                            program_name = short_desc
                            if episode_index and int(episode_index) > 0:
                                program_name += f" 第{episode_index}集"

                            programs.append(Program(
                                channel_id=channel.channel_id,
                                title=program_name,
                                start_time=start_time,
                                end_time=end_time,
                                description="",
                                raw_data={
                                    'short_desc': short_desc,
                                    'episode_index': episode_index,
                                    'start_time_str': start_time_str,
                                    'end_time_str': end_time_str
                                }
                            ))

                except Exception as e:
                    self.logger.warning(f"⚠️ 解析 EPG 项目失败: {e}")
                    continue

        return programs


# Create platform instance
hoy_platform = HOYPlatform()


# Legacy functions for backward compatibility
def parse_epg_xml(xml_content, channel_name):
    """Legacy function - parse EPG XML"""
    try:
        # Create a temporary channel object
        channel = Channel(channel_id="temp", name=channel_name)
        programs = hoy_platform._parse_epg_xml(xml_content, channel)

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
        logger.error(f"❌ 旧版 parse_epg_xml 错误: {e}")
        return []


async def get_hoy_lists():
    """Legacy function - get HOY channel list"""
    try:
        channels = await hoy_platform.fetch_channels()

        # Convert to legacy format
        channel_list = []
        for channel in channels:
            channel_list.append({
                "channelName": channel.name,
                "rawEpg": channel.extra_data.get('epg_url', ''),
                "logo": channel.extra_data.get('logo', '')
            })

        return channel_list
    except Exception as e:
        logger.error(f"❌ 旧版 get_hoy_lists 错误: {e}")
        return []


async def get_hoy_epg():
    """Legacy function - fetch HOY EPG data"""
    try:
        channels = await hoy_platform.fetch_channels()
        programs = await hoy_platform.fetch_programs(channels)

        # Convert to legacy format
        raw_channels = []
        raw_programs = []

        for channel in channels:
            raw_channels.append({
                "channelName": channel.name,
                "rawEpg": channel.extra_data.get('epg_url', ''),
                "logo": channel.extra_data.get('logo', '')
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
        logger.error(f"❌ 旧版 get_hoy_epg 函数错误: {e}", exc_info=True)
        return [], []