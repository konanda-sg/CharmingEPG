import xml.etree.ElementTree as ET
from typing import List

from ..logger import get_logger
from .base import BaseEPGPlatform, Channel, Program

logger = get_logger(__name__)


class CNEpgPlatform(BaseEPGPlatform):
    """CN (epg.pw) EPG platform implementation"""

    def __init__(self):
        super().__init__("cn")
        self.epg_url = "https://epg.pw/xmltv/epg_CN.xml"

    async def fetch_channels(self) -> List[Channel]:
        """Fetch channel list from CN EPG XML"""
        self.logger.info("📡 正在从 CN EPG 获取频道列表")

        response = self.http_client.get(self.epg_url)

        # Parse XML to extract channels
        root = ET.fromstring(response.text)
        channels = []

        for channel_elem in root.findall('channel'):
            channel_id = channel_elem.get('id', '')
            display_name_elem = channel_elem.find('display-name')
            channel_name = display_name_elem.text if display_name_elem is not None else channel_id

            if channel_id:
                channels.append(Channel(
                    channel_id=channel_id,
                    name=channel_name,
                    raw_data={'xml_element': channel_elem}
                ))

        self.logger.info(f"📺 从 CN EPG 发现 {len(channels)} 个频道")
        return channels

    async def fetch_programs(self, channels: List[Channel]) -> List[Program]:
        """Fetch program data from CN EPG XML"""
        self.logger.info(f"📡 正在抓取 {len(channels)} 个频道的节目数据")

        response = self.http_client.get(self.epg_url)
        root = ET.fromstring(response.text)
        programs = []

        # Create a set of valid channel IDs for quick lookup
        valid_channel_ids = {ch.channel_id for ch in channels}

        for programme_elem in root.findall('programme'):
            try:
                channel_id = programme_elem.get('channel', '')

                # Only include programs for channels we have
                if channel_id in valid_channel_ids:
                    start_time_str = programme_elem.get('start', '')
                    stop_time_str = programme_elem.get('stop', '')

                    title_elem = programme_elem.find('title')
                    title = title_elem.text if title_elem is not None else ''

                    desc_elem = programme_elem.find('desc')
                    description = desc_elem.text if desc_elem is not None else ''

                    # Parse time strings (format: YYYYMMDDHHMMSS +0800)
                    start_time = self._parse_epg_time(start_time_str)
                    stop_time = self._parse_epg_time(stop_time_str)

                    if start_time and stop_time:
                        programs.append(Program(
                            channel_id=channel_id,
                            title=title,
                            start_time=start_time,
                            end_time=stop_time,
                            description=description,
                            raw_data={'xml_element': programme_elem}
                        ))

            except Exception as e:
                self.logger.warning(f"⚠️ 解析节目数据失败: {e}")
                continue

        self.logger.info(f"📊 总共抓取了 {len(programs)} 个节目")
        return programs

    def _parse_epg_time(self, time_str: str):
        """Parse EPG time format (YYYYMMDDHHMMSS +0800)"""
        try:
            from datetime import datetime
            import pytz

            # Remove timezone info and parse base datetime
            time_part = time_str.split()[0] if ' ' in time_str else time_str
            dt = datetime.strptime(time_part, '%Y%m%d%H%M%S')

            # Add Shanghai timezone
            shanghai_tz = pytz.timezone('Asia/Shanghai')
            return shanghai_tz.localize(dt)

        except Exception as e:
            self.logger.warning(f"⚠️ 解析时间字符串 '{time_str}' 失败: {e}")
            return None

    async def get_raw_xml(self) -> str:
        """Get the raw XML content from epg.pw"""
        self.logger.info("📡 正在从 CN EPG 获取原始 XML")

        response = self.http_client.get(self.epg_url)

        # Parse and re-serialize to ensure clean XML
        root = ET.fromstring(response.text)
        return ET.tostring(root, encoding='utf-8').decode('utf-8')


# Create platform instance
cn_epg_platform = CNEpgPlatform()


# Legacy function for backward compatibility
async def get_cn_channels_epg():
    """Legacy function - fetch CN EPG as raw XML"""
    try:
        return await cn_epg_platform.get_raw_xml()
    except Exception as e:
        logger.error(f"❌ 旧版 get_cn_channels_epg 函数错误: {e}", exc_info=True)
        return ""