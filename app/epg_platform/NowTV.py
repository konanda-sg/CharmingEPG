import json
import pytz
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup

from ..config import Config
from ..logger import get_logger
from .base import BaseEPGPlatform, Channel, Program

logger = get_logger(__name__)


class NowTVPlatform(BaseEPGPlatform):
    """NowTV EPG platform implementation"""

    def __init__(self):
        super().__init__("nowtv")
        self.base_url = "https://nowplayer.now.com"
        self.channels_cache = []
        self.channel_nums_cache = []

    async def fetch_channels(self) -> List[Channel]:
        """Fetch channel list from NowTV website"""
        self.logger.info("📡 正在从 NowTV 获取频道列表")

        headers = self.get_default_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': f'{self.base_url}/channels',
            'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,ar-EG;q=0.6,ar;q=0.5'
        })

        # Use cookies to set language to Chinese
        response = self.http_client.get(
            f"{self.base_url}/channels",
            headers=headers,
            cookies={'LANG': 'zh'}
        )

        soup = BeautifulSoup(response.text, 'html.parser')
        channels = []
        channel_nums = []

        # Find all channel items
        items = soup.find_all('div', class_='product-item')

        for item in items:
            # Get logo image URL
            img_tag = item.find('img')
            logo = img_tag['src'] if img_tag else None

            # Get channel name
            name_tag = item.find('p', class_='img-name')
            name = name_tag.text if name_tag else None

            # Get channel number
            channel_tag = item.find('p', class_='channel')
            channel_no = channel_tag.text.replace('CH', '') if channel_tag else None

            if name and channel_no:
                channels.append(Channel(
                    channel_id=channel_no,
                    name=name,
                    channel_no=channel_no,
                    logo=logo,
                    raw_data={
                        'logo': logo,
                        'name': name,
                        'channelNo': channel_no
                    }
                ))
                channel_nums.append(channel_no)

        # Cache for later use
        self.channels_cache = channels
        self.channel_nums_cache = channel_nums

        self.logger.info(f"📺 从 NowTV 发现 {len(channels)} 个频道")
        return channels

    async def fetch_programs(self, channels: List[Channel]) -> List[Program]:
        """Fetch program data for all channels"""
        self.logger.info(f"📡 正在抓取 {len(channels)} 个频道的节目数据")

        # Get channel numbers for EPG fetching
        channel_numbers = [ch.extra_data.get('channelNo') for ch in channels if ch.extra_data.get('channelNo')]

        if not channel_numbers:
            self.logger.warning("⚠️ 未找到用于 EPG 抓取的频道编号")
            return []

        # Fetch 7-day EPG data
        epg_data = await self._fetch_7day_epg(channel_numbers)
        programs = []

        # Process EPG data for each day
        for day in range(1, 8):  # Days 1-7
            day_epg = epg_data.get(day, [])

            for channel_index, channel_epg in enumerate(day_epg):
                if channel_index < len(channel_numbers):
                    channel_no = channel_numbers[channel_index]
                    channel_name = self._find_channel_name(channels, channel_no)

                    for epg_item in channel_epg:
                        try:
                            start_timestamp = epg_item.get("start", 0) / 1000
                            end_timestamp = epg_item.get("end", 0) / 1000

                            start_time = self._timestamp_to_datetime(start_timestamp)
                            end_time = self._timestamp_to_datetime(end_timestamp)

                            programs.append(Program(
                                channel_id=channel_no,
                                title=epg_item.get("name", ""),
                                start_time=start_time,
                                end_time=end_time,
                                description="",
                                raw_data=epg_item
                            ))

                        except Exception as e:
                            self.logger.warning(f"⚠️ 解析节目数据失败: {e}")
                            continue

        self.logger.info(f"📊 总共抓取了 {len(programs)} 个节目")
        return programs

    async def _fetch_7day_epg(self, channel_numbers: List[str]) -> dict:
        """Fetch 7-day EPG data from NowTV API"""
        epg_cache = {}

        headers = self.get_default_headers({
            'Accept': 'text/plain, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': f'{self.base_url}/tvguide',
            'X-Requested-With': 'XMLHttpRequest',
        })

        cookies = {'LANG': 'zh'}

        for day in range(1, 8):  # Days 1-7
            try:
                params = {
                    'channelIdList[]': channel_numbers,
                    'day': str(day),
                }

                response = self.http_client.get(
                    f'{self.base_url}/tvguide/epglist',
                    headers=headers,
                    cookies=cookies,
                    params=params
                )

                self.logger.debug(f"🔍 第 {day} 天的 EPG 请求: 状态码 {response.status_code}")

                if response.status_code == 200:
                    epg_cache[day] = response.json()
                else:
                    self.logger.warning(f"⚠️ 获取第 {day} 天的 EPG 失败: 状态码 {response.status_code}")
                    epg_cache[day] = []

            except Exception as e:
                self.logger.error(f"❌ 获取第 {day} 天的 EPG 错误: {e}")
                epg_cache[day] = []

        return epg_cache

    def _find_channel_name(self, channels: List[Channel], channel_no: str) -> str:
        """Find channel name by channel number"""
        for channel in channels:
            if channel.extra_data.get('channelNo') == channel_no:
                return channel.name
        return f"Channel {channel_no}"

    def _timestamp_to_datetime(self, timestamp: float) -> datetime:
        """Convert timestamp to Shanghai timezone datetime"""
        utc_dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
        target_tz = pytz.timezone('Asia/Shanghai')
        local_dt = utc_dt.astimezone(target_tz)
        return local_dt

    async def generate_epg_xml_direct(self, channel_numbers: List[str] = None) -> bytes:
        """Generate EPG XML directly (legacy method)"""
        if not channel_numbers:
            channels = await self.fetch_channels()
            channel_numbers = [ch.extra_data.get('channelNo') for ch in channels if ch.extra_data.get('channelNo')]

        epg_data = await self._fetch_7day_epg(channel_numbers)
        channels = self.channels_cache if self.channels_cache else await self.fetch_channels()

        tv = ET.Element("tv", {"generator-info-name": f"{Config.APP_NAME} NowTV"})

        # Create channel elements
        for channel_no in channel_numbers:
            channel_name = self._find_channel_name(channels, channel_no)
            channel_elem = ET.SubElement(tv, "channel", id=channel_name)
            display_name = ET.SubElement(channel_elem, "display-name", lang="zh")
            display_name.text = channel_name

        # Create programme elements
        for day in range(1, 8):
            day_epg = epg_data.get(day, [])
            for channel_index, channel_epg in enumerate(day_epg):
                if channel_index < len(channel_numbers):
                    channel_no = channel_numbers[channel_index]
                    channel_name = self._find_channel_name(channels, channel_no)

                    for epg_item in channel_epg:
                        try:
                            start_timestamp = epg_item.get("start", 0) / 1000
                            end_timestamp = epg_item.get("end", 0) / 1000

                            start_time_str = self._timestamp_to_timezone_str(start_timestamp)
                            end_time_str = self._timestamp_to_timezone_str(end_timestamp)

                            programme = ET.SubElement(tv, "programme",
                                                    channel=channel_name,
                                                    start=start_time_str,
                                                    stop=end_time_str)
                            title = ET.SubElement(programme, "title", lang="zh")
                            title.text = epg_item.get("name", "")

                        except Exception as e:
                            self.logger.warning(f"⚠️ 创建节目元素失败: {e}")
                            continue

        return ET.tostring(tv, encoding='utf-8')

    def _timestamp_to_timezone_str(self, timestamp: float) -> str:
        """Convert timestamp to timezone string format"""
        utc_dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
        target_tz = pytz.timezone('Asia/Shanghai')
        local_dt = utc_dt.astimezone(target_tz)
        return local_dt.strftime('%Y%m%d%H%M%S %z')


# Create platform instance
nowtv_platform = NowTVPlatform()


# Legacy functions for backward compatibility
def get_official_channel_list():
    """Legacy function - get channel list (synchronous)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use run()
            # This is a limitation of the legacy sync function
            logger.warning("⚠️ 在异步上下文中调用 get_official_channel_list - 返回空列表")
            return []
        else:
            channels = loop.run_until_complete(nowtv_platform.fetch_channels())
            nowtv_platform.channels_cache = channels
            nowtv_platform.channel_nums_cache = [ch.extra_data.get('channelNo') for ch in channels]
            return [ch.extra_data for ch in channels]
    except Exception as e:
        logger.error(f"❌ 旧版 get_official_channel_list 错误: {e}")
        return []


async def request_nowtv_today_epg():
    """Legacy function - fetch NowTV EPG as XML"""
    try:
        channels = await nowtv_platform.fetch_channels()
        channel_numbers = [ch.extra_data.get('channelNo') for ch in channels if ch.extra_data.get('channelNo')]
        xml_bytes = await nowtv_platform.generate_epg_xml_direct(channel_numbers)
        return xml_bytes
    except Exception as e:
        logger.error(f"❌ 旧版 request_nowtv_today_epg 错误: {e}", exc_info=True)
        return b""


async def get_now_tv_guide_to_epg(channel_numbers, cache_keyword):
    """Legacy function - generate EPG XML"""
    try:
        xml_bytes = await nowtv_platform.generate_epg_xml_direct(channel_numbers)
        return xml_bytes
    except Exception as e:
        logger.error(f"❌ 旧版 get_now_tv_guide_to_epg 错误: {e}", exc_info=True)
        return b""


def time_stamp_to_timezone_str(timestamp_s):
    """Legacy utility function"""
    return nowtv_platform._timestamp_to_timezone_str(timestamp_s)


def find_channel_name(channels, channel_no):
    """Legacy utility function"""
    for item in channels:
        if item.get("channelNo") == channel_no:
            return item.get("name")
    return f"Channel {channel_no}"


async def fetch_7day_epg(channel_numbers):
    """Legacy function - fetch 7-day EPG"""
    try:
        return await nowtv_platform._fetch_7day_epg(channel_numbers)
    except Exception as e:
        logger.error(f"❌ 旧版 fetch_7day_epg 错误: {e}", exc_info=True)
        return {}