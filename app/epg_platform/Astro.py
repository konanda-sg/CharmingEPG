import math

import requests
from urllib.parse import urlparse
from datetime import datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo
import pytz
from loguru import logger

from app.utils import has_chinese

UA = "Mozilla/5.0"
REFERER = "https://astrogo.astro.com.my/"
C_TOKEN = "v:1!r:80800!ur:GUEST_REGION!community:Malaysia%20Live!t:k!dt:PC!f:Astro_unmanaged!pd:CHROME-FF!pt:Adults"
token = ""

"""
原理
1. https://sg-sg-sg.astro.com.my:9443/oauth2/authorize 在302重定向的url里获取游客token，有效期3小时
   有效期在这里没什么用，因为每天查询我都重新拉取token。
    
2. https://sg-sg-sg.astro.com.my:9443/ctap/r1.6.0/shared/channels 获取频道列表，拿到频道数量、第一个频道id、频道名称
   这里我在获取频道名之后，移除HD字样，作为相对正式的频道名。

3. https://sg-sg-sg.astro.com.my:9443/ctap/r1.6.0/shared/grid 获取epg
   其中需要传入：
   开始时间(utc字符串)
   查询时长（小时）
   开始频道id
   查询频道数量
   
   看这些参数，估计是直接丢进sql里。
   所以我尝试用第一个id+频道总数也是能查询到的。
   
   注意：查询当天的epg，不能获取全天的，开始时间需要以当前时间向下取整（以半小时为整），查询时长就是从当前时间到第二天0点0分的小时数（往上取整）
   比如现在我在写这一段的时间是15:34，就需要向下取整为15:30，然后15:30到第二天0点就是9小时（向上取整）
"""


async def get_astro_epg():
    global token
    token = get_access_token()
    channel_count, channels, first_id = query_channels()
    merged_channels = {}
    for day in range(0, 7):
        logger.info("Astro 正在获取Day " + str(day))
        date_str, duration = get_date_str(day)
        raw_epg = query_epg(date_str, duration, channel_count, first_id)
        if raw_epg.get("channels"):
            for channel in raw_epg["channels"]:
                channel_id = channel["id"]
                schedule = channel.get("schedule", [])
                if channel_id not in merged_channels:
                    merged_channels[channel_id] = {
                        "id": channel_id,
                        "schedule": []
                    }
                merged_channels[channel_id]["schedule"].extend(schedule)
    epgResult = []
    for channel in merged_channels:
        channelName = find_channel_name_by_id(channels, channel)
        for program in merged_channels[channel]["schedule"]:
            start_time = program.get("startDateTime")
            duration = program.get("duration")
            if start_time and duration:
                start_time_with_tz, end_time_with_tz = utc_to_local(start_time, duration)
                title = program.get("title", "")
                description = program.get("synopsis", "")
                episodeNumber = program.get("episodeNumber")
                if has_chinese(title) or has_chinese(description):
                    episodeNumber = f" 第{episodeNumber}集" if episodeNumber else ""
                else:
                    episodeNumber = f" Ep{episodeNumber}" if episodeNumber else ""
                epgResult.append(
                    {"channelName": channelName, "programName": title + episodeNumber,
                     "description": description,
                     "start": start_time_with_tz, "end": end_time_with_tz
                     }
                )
    return channels, epgResult


def find_channel_name_by_id(channels, channel_id):
    for channel in channels:
        if channel['channelId'] == channel_id:
            return channel['channelName']


def utc_to_local(start_time, duration):
    # 1. 字符串转UTC时间对象
    start_time_utc = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.000Z")
    start_time_utc = pytz.utc.localize(start_time_utc)

    # 2. 计算结束时间（UTC）
    end_time_utc = start_time_utc + timedelta(seconds=duration)

    # 3. 转成上海时间
    shanghai_tz = pytz.timezone('Asia/Shanghai')
    start_time_shanghai = start_time_utc.astimezone(shanghai_tz)
    end_time_shanghai = end_time_utc.astimezone(shanghai_tz)
    return start_time_shanghai, end_time_shanghai


def extract_fragment_params(location_url):
    """
    解析location header中的fragment参数（#之后的access_token等）
    """
    parsed = urlparse(location_url)
    fragment = parsed.fragment
    params = dict()
    for item in fragment.split("&"):
        if "=" in item:
            key, value = item.split("=", 1)
            params[key] = value
    return params


def get_access_token():
    url = "https://sg-sg-sg.astro.com.my:9443/oauth2/authorize"
    params = {
        "client_id": "browser",
        "state": "guestUserLogin",
        "response_type": "token",
        "redirect_uri": "https://astrogo.astro.com.my",
        "scope": "urn:synamedia:vcs:ovp:guest-user",
        "prompt": "none",
    }
    headers = {
        "User-Agent": UA,
        "Referer": REFERER,
    }
    session = requests.Session()
    response = session.get(url, headers=headers, allow_redirects=False, params=params)
    if "Location" not in response.headers:
        logger.error("未找到重定向Location!")
        return None
    location = response.headers["Location"]
    params = extract_fragment_params(location)
    access_token = params.get("access_token")
    if access_token:
        logger.info("Astro access_token =", access_token)
        return access_token
    else:
        logger.error("Astro 未提取到access_token！完整location:", location)
        return None


def get_date_str(date_delta):
    now = datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(days=date_delta)
    if date_delta == 0:
        # 向下取整到最近的半小时
        minute = now.minute
        rounded_minute = 0 if minute < 30 else 30
        target_time = now.replace(minute=rounded_minute, second=0, microsecond=0)
        # 明天凌晨0点
        next_day = (target_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        # 时长（秒）
        dur_seconds = (next_day - target_time).total_seconds()
        # 向上取整到小时
        duration = math.ceil(dur_seconds / 3600)
    else:
        target_time = datetime.combine(now.date(), time(0, 0), tzinfo=ZoneInfo("Asia/Shanghai"))
        duration = 24
    target_time_utc = target_time.astimezone(timezone.utc)
    iso_str = target_time_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    return iso_str, duration


def query_channels():
    url = "https://sg-sg-sg.astro.com.my:9443/ctap/r1.6.0/shared/channels"
    params = {
        "clientToken": C_TOKEN
    }
    headers = {
        "User-Agent": UA,
        "Referer": REFERER,
        "Authorization": "Bearer " + token,
        "Accept-Language": "zh"
    }
    session = requests.Session()
    response = session.get(url, headers=headers, params=params)
    if response.status_code == 200:
        channels_resp = response.json()
        channel_count = channels_resp["count"]
        channels = []
        first_id = channels_resp["channels"][0]["id"]
        for channel in channels_resp["channels"]:
            logo = ""
            for media in channel["media"]:
                if media["type"] == "regular":
                    logo = media["url"]
            if logo == "" and len(channel["media"]) > 0:
                logo = channel["media"][0]["url"]

            channels.append(
                {"channelName": channel["name"].replace(" HD", "").strip(), "channelId": channel["id"], "logo": logo})
        return channel_count, channels, first_id


def query_epg(start_date, duration, channel_count, first_id):
    url = "https://sg-sg-sg.astro.com.my:9443/ctap/r1.6.0/shared/grid"
    params = {
        "startDateTime": start_date,
        "channelId": first_id,
        "limit": channel_count,
        "genreId": "",
        "isPlayable": "true",
        "duration": duration,
        "clientToken": C_TOKEN
    }
    headers = {
        "User-Agent": UA,
        "Referer": REFERER,
        "Authorization": "Bearer " + token,
        "Accept-Language": "zh"
    }
    session = requests.Session()
    response = session.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {}

# if __name__ == '__main__':
#     # get_astro_epg()
#     get_date_str(0)
