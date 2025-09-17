import os
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException
from fastapi.responses import Response

from .config import Config
from .logger import get_logger

logger = get_logger(__name__)


class EPGFileManager:
    """Manages EPG file operations including reading, writing, and aggregation"""

    @staticmethod
    def get_epg_file_path(platform: str, date_str: str = None) -> str:
        """Get the file path for EPG data"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        return Config.get_epg_file_path(platform, date_str)

    @staticmethod
    def ensure_directory_exists(file_path: str):
        """Create directory if it doesn't exist"""
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")

    @staticmethod
    def read_epg_file(platform: str, date_str: str = None) -> Optional[bytes]:
        """
        Read EPG file content for a platform

        Args:
            platform: Platform name
            date_str: Date string (YYYYMMDD), defaults to today

        Returns:
            File content as bytes or None if file doesn't exist
        """
        file_path = EPGFileManager.get_epg_file_path(platform, date_str)

        if not os.path.exists(file_path):
            logger.warning(f"EPG file not found: {file_path}")
            return None

        try:
            with open(file_path, "rb") as file:
                content = file.read()
                logger.debug(f"Successfully read EPG file: {file_path} ({len(content)} bytes)")
                return content
        except Exception as e:
            logger.error(f"Failed to read EPG file {file_path}: {e}")
            return None

    @staticmethod
    def save_epg_file(platform: str, content: bytes, date_str: str = None) -> bool:
        """
        Save EPG content to file

        Args:
            platform: Platform name
            content: XML content as bytes
            date_str: Date string (YYYYMMDD), defaults to today

        Returns:
            True if successful, False otherwise
        """
        file_path = EPGFileManager.get_epg_file_path(platform, date_str)

        try:
            EPGFileManager.ensure_directory_exists(file_path)

            with open(file_path, "wb") as file:
                file.write(content)

            logger.info(f"Saved EPG file: {file_path} ({len(content)} bytes)")
            return True

        except Exception as e:
            logger.error(f"Failed to save EPG file {file_path}: {e}")
            return False

    @staticmethod
    def delete_old_epg_files(platform: str, keep_current: bool = True) -> int:
        """
        Delete old EPG files for a platform

        Args:
            platform: Platform name
            keep_current: Whether to keep today's file

        Returns:
            Number of files deleted
        """
        try:
            current_date = datetime.now().strftime('%Y%m%d')
            current_file = f"{platform}_{current_date}.xml"
            epg_dir = os.path.dirname(EPGFileManager.get_epg_file_path(platform))

            if not os.path.exists(epg_dir):
                return 0

            deleted_count = 0
            for file_name in os.listdir(epg_dir):
                if file_name.endswith(".xml"):
                    if not keep_current or file_name != current_file:
                        file_path = os.path.join(epg_dir, file_name)
                        os.remove(file_path)
                        deleted_count += 1
                        logger.debug(f"Deleted old EPG file: {file_name}")

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old EPG files for {platform}")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete old EPG files for {platform}: {e}")
            return 0

    @staticmethod
    def aggregate_epg_files(platforms: List[str]) -> Response:
        """
        Aggregate EPG files from multiple platforms

        Args:
            platforms: List of platform names to aggregate

        Returns:
            FastAPI Response with aggregated XML content

        Raises:
            HTTPException: If no EPG data is available
        """
        logger.info(f"Aggregating EPG data for platforms: {platforms}")

        merged_root = ET.Element("tv")
        merged_root.set("generator-info-name", f"{Config.APP_NAME} v{Config.APP_VERSION}")
        merged_root.set("generator-info-url", "https://github.com/your-repo/CharmingEPG")

        channels_seen = set()
        total_channels = 0
        total_programs = 0

        for platform in platforms:
            content = EPGFileManager.read_epg_file(platform)
            if not content:
                logger.warning(f"No EPG data found for platform: {platform}")
                continue

            try:
                platform_root = ET.fromstring(content)

                # Process channels (first-come-first-served for duplicates)
                platform_channels = 0
                platform_programs = 0

                for channel in platform_root.findall("./channel"):
                    channel_id = channel.get("id")
                    if channel_id and channel_id not in channels_seen:
                        channels_seen.add(channel_id)
                        merged_root.append(channel)
                        platform_channels += 1

                        # Add all programs for this channel
                        for programme in platform_root.findall(f"./programme[@channel='{channel_id}']"):
                            merged_root.append(programme)
                            platform_programs += 1

                total_channels += platform_channels
                total_programs += platform_programs

                logger.debug(
                    f"Merged {platform_channels} channels and {platform_programs} programs from {platform}"
                )

            except ET.ParseError as e:
                logger.error(f"Failed to parse XML for platform {platform}: {e}")
                continue

        if total_channels == 0:
            logger.error("No valid EPG data found in any platform")
            raise HTTPException(status_code=404, detail="No EPG data available")

        # Convert merged XML to string
        merged_xml = ET.tostring(merged_root, encoding="utf-8", xml_declaration=True)

        logger.info(f"Successfully aggregated {total_channels} channels and {total_programs} programs")

        return Response(
            content=merged_xml,
            media_type="application/xml",
            headers={
                "Content-Disposition": "inline; filename=epg.xml",
                "X-Total-Channels": str(total_channels),
                "X-Total-Programs": str(total_programs),
                "X-Platforms": ",".join(platforms)
            }
        )

    @staticmethod
    def get_single_platform_epg(platform: str) -> Response:
        """
        Get EPG data for a single platform

        Args:
            platform: Platform name

        Returns:
            FastAPI Response with XML content

        Raises:
            HTTPException: If EPG file is not found
        """
        content = EPGFileManager.read_epg_file(platform)

        if content is None:
            logger.error(f"EPG file not found for platform: {platform}")
            raise HTTPException(
                status_code=404,
                detail=f"EPG data not available for platform: {platform}"
            )

        # Parse XML to get channel and program counts for headers
        try:
            root = ET.fromstring(content)
            channel_count = len(root.findall("./channel"))
            program_count = len(root.findall("./programme"))

            logger.info(f"Serving EPG for {platform}: {channel_count} channels, {program_count} programs")

            return Response(
                content=content,
                media_type="application/xml",
                headers={
                    "Content-Disposition": f"inline; filename={platform}_epg.xml",
                    "X-Platform": platform,
                    "X-Total-Channels": str(channel_count),
                    "X-Total-Programs": str(program_count)
                }
            )

        except ET.ParseError:
            logger.warning(f"Invalid XML content for platform {platform}, serving as-is")
            return Response(
                content=content,
                media_type="application/xml",
                headers={
                    "Content-Disposition": f"inline; filename={platform}_epg.xml",
                    "X-Platform": platform
                }
            )