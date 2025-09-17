import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
from loguru import logger

from app.utils import has_chinese, utc_to_utc8_datetime


async def get_starhub_epg():
    programme_list = []
    channels = []
    try:
        channels = request_channels()
        logger.info(f"[Starhub]获取到共{len(channels)}个频道")
        for channel in channels:
            channel_program_list = request_epg(channel['channelId'], channel['channelName'])
            programme_list.extend(channel_program_list)
    except Exception as e:
        logger.error(f"Error requesting EPG for {channel['channelName']}: {e}")
    return channels, programme_list


def request_channels():
    url = 'https://waf-starhub-metadata-api-p001.ifs.vubiquity.com/v3.1/epg/channels'
    params = {
        "locale": 'zh',
        "locale_default": "en_US",
        "device": "1",
        "limit": "150",
        "page": "1"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    }
    result = requests.get(url, params=params, headers=headers)
    result.raise_for_status()
    result_json = result.json()
    channels = []
    for channel in result_json['resources']:
        if channel['metatype'] == 'Channel':
            channels.append({"channelName": channel['title'], "channelId": channel['id']})

    return channels


def request_epg(channel_id, channel_name):
    logger.info(f"[Starhub]正在获取 {channel_name} 节目表,ID={channel_id}...")
    url = 'https://waf-starhub-metadata-api-p001.ifs.vubiquity.com/v3.1/epg/schedules'

    tz = ZoneInfo('Asia/Shanghai')

    # 获取今天0点0分0秒
    today_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    today_timestamp = int(today_start.timestamp())

    # 获取6天后的23点59分59秒
    six_days_later = today_start + timedelta(days=6)
    six_days_later_end = six_days_later.replace(hour=23, minute=59, second=59)
    six_days_later_timestamp = int(six_days_later_end.timestamp())

    params = {
        "locale": 'zh',
        "locale_default": "en_US",
        "device": "1",
        "limit": "500",
        "page": "1",
        "in_channel_id": channel_id,
        "gt_end": str(today_timestamp),  # 这个才是开始时间 通常是东八区0点0分0秒
        "lt_start": str(six_days_later_timestamp),  # 这个才是结束时间，通常是东八区23点59分59秒
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    }

    result = requests.get(url, params=params, headers=headers)
    result.raise_for_status()
    result_json = result.json()
    program_list = []
    for program in result_json['resources']:
        if program['metatype'] == 'Schedule':
            episodeNumber = program.get("episode_number")
            title = program['title']
            description = program['description']
            if has_chinese(title) or has_chinese(description):
                episodeNumber = f" 第{episodeNumber}集" if episodeNumber else ""
            else:
                episodeNumber = f" Ep{episodeNumber}" if episodeNumber else ""
            program_list.append({
                "channelName": channel_name,
                "programName": title + episodeNumber,
                "description": description,
                "start": utc_to_utc8_datetime(program['start']),
                "end": utc_to_utc8_datetime(program['end'])
            })
    return program_list


if __name__ == '__main__':
    request_epg("38251a1a-9368-410c-9dc5-ab806d74420f")
