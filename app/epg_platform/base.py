import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

from ..config import Config
from ..logger import get_logger
from ..http_client import get_http_client
from ..epg.EpgGenerator import generateEpg

logger = get_logger(__name__)


class Channel:
    """Data class for channel information"""
    def __init__(self, channel_id: str, name: str, **kwargs):
        self.channel_id = channel_id
        self.name = name
        self.extra_data = kwargs

    def __repr__(self):
        return f"Channel(id={self.channel_id}, name={self.name})"


class Program:
    """Data class for program information"""
    def __init__(self, channel_id: str, title: str, start_time: datetime,
                 end_time: datetime, description: str = "", **kwargs):
        self.channel_id = channel_id
        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.description = description
        self.extra_data = kwargs

    def __repr__(self):
        return f"Program(channel={self.channel_id}, title={self.title}, start={self.start_time})"


class BaseEPGPlatform(ABC):
    """Base class for all EPG platforms with common functionality"""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.logger = get_logger(f"platform.{platform_name}")
        self.http_client = get_http_client()

    @abstractmethod
    async def fetch_channels(self) -> List[Channel]:
        """Fetch channel list from the platform"""
        pass

    @abstractmethod
    async def fetch_programs(self, channels: List[Channel]) -> List[Program]:
        """Fetch program data for the given channels"""
        pass

    def get_epg_file_path(self, date_str: str = None) -> str:
        """Get the file path for EPG data"""
        if date_str is None:
            date_str = self._get_date_str()
        return Config.get_epg_file_path(self.platform_name, date_str)

    def _get_date_str(self) -> str:
        """Get current date string in YYYYMMDD format"""
        return datetime.now().strftime('%Y%m%d')

    def _ensure_directory_exists(self, file_path: str):
        """Create directory if it doesn't exist"""
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            self.logger.info(f"📌 创建目录: {directory}")

    async def generate_epg_xml(self, channels: List[Channel], programs: List[Program]) -> bytes:
        """Generate EPG XML from channels and programs data"""
        self.logger.info(f"🛠️ 正在生成EPG XML：{len(channels)}个频道，{len(programs)}个节目")
        return await generateEpg(channels, programs)

    async def save_epg_to_file(self, xml_content: bytes, file_path: str):
        """Save EPG XML content to file"""
        self._ensure_directory_exists(file_path)

        with open(file_path, "wb") as file:
            file.write(xml_content)

        file_size = len(xml_content)
        self.logger.info(f"💾 保存EPG数据到 {file_path} ({file_size} 字节)")

    def _delete_old_epg_files(self):
        """Delete old EPG files, keeping only today's file"""
        try:
            today_file = os.path.basename(self.get_epg_file_path())
            epg_dir = os.path.dirname(self.get_epg_file_path())

            if not os.path.exists(epg_dir):
                return

            deleted_count = 0
            for file_name in os.listdir(epg_dir):
                if file_name.endswith(".xml") and file_name != today_file:
                    file_path = os.path.join(epg_dir, file_name)
                    os.remove(file_path)
                    deleted_count += 1
                    self.logger.debug(f"🗑️ 删除旧EPG文件: {file_name}")

            if deleted_count > 0:
                self.logger.info(f"🧹 清理{self.platform_name}的{deleted_count}个旧EPG文件")

        except Exception as e:
            self.logger.error(f"❌ 删除{self.platform_name}的旧EPG文件失败: {e}")

    async def update_epg(self, force: bool = False) -> bool:
        """
        Main method to update EPG data for this platform

        Args:
            force: Force update even if today's file already exists

        Returns:
            bool: True if update was successful, False otherwise
        """
        file_path = self.get_epg_file_path()

        # Check if today's EPG already exists
        if not force and os.path.exists(file_path):
            self.logger.info(f"✅ {self.platform_name}的今日EPG数据已存在，跳过更新")
            return True

        try:
            self.logger.info(f"🚀 开始EPG更新：{self.platform_name}")

            # Fetch data
            channels = await self.fetch_channels()
            if not channels:
                self.logger.warning(f"⚠️ {self.platform_name}未找到频道数据")
                return False

            programs = await self.fetch_programs(channels)
            if not programs:
                self.logger.warning(f"⚠️ {self.platform_name}未找到节目数据")
                return False

            # Generate XML
            xml_content = await self.generate_epg_xml(channels, programs)

            # Save to file
            await self.save_epg_to_file(xml_content, file_path)

            # Clean up old files
            self._delete_old_epg_files()

            self.logger.info(f"✨ 成功更新{self.platform_name}的EPG数据")
            return True

        except Exception as e:
            self.logger.error(f"❌ 更新{self.platform_name}的EPG数据失败: {e}", exc_info=True)
            return False

    def get_default_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get default headers for HTTP requests"""
        headers = {
            "User-Agent": Config.DEFAULT_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6",
            "Cache-Control": "no-cache",
        }

        if additional_headers:
            headers.update(additional_headers)

        return headers