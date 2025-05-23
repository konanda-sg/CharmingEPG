import os

import pytz
import requests
from datetime import datetime, timedelta

from dotenv import load_dotenv
from loguru import logger

load_dotenv(verbose=True, override=True)
PROXY_HTTP = os.getenv("PROXY_HTTP", None)
PROXY_HTTPS = os.getenv("PROXY_HTTPS", None)
PROXIES = None

platform_name = "tvb"

if PROXY_HTTP and PROXY_HTTPS:
    PROXIES = {
        "http": PROXY_HTTP,
        "https": PROXY_HTTP
    }


async def get_channels(force: bool = False):
    logger.info(f"平台【{platform_name}】 正在执行更新")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6",
        "Cache-Control": "no-cache",
        "Origin": "https://www.mytvsuper.com",
        "Pragma": "no-cache",
        "Referer": "https://www.mytvsuper.com/",
        "Sec-CH-UA": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }

    params = {
        "platform": "web",
        "country_code": "HK",
        "profile_class": 'general',
    }

    response = requests.get("https://content-api.mytvsuper.com/v1/channel/list", headers=headers, params=params,
                            proxies=PROXIES)
    if response.status_code == 200:
        data = response.json()
        logger.info(data)

        rawChannels = []
        rawPrograms = []
        for channel in data['channels']:
            channelName = channel['name_tc'].replace(" (免費)", "")
            rawChannels.append({"channelName": channelName})
            programData = await request_epg(network_code=channel['network_code'], channel_name=channelName)
            rawPrograms.extend(programData)

        return rawChannels, rawPrograms
    return [], []


async def request_epg(network_code, channel_name):
    logger.info("正在获取:" + channel_name)
    # 获取当前日期
    formatted_current_date = datetime.now().strftime('%Y%m%d')

    # 获取7天后的日期
    date_after_seven_days = datetime.now() + timedelta(days=7)
    formatted_date_after_seven_days = date_after_seven_days.strftime('%Y%m%d')

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6",
        "Cache-Control": "no-cache",
        "Origin": "https://www.mytvsuper.com",
        "Pragma": "no-cache",
        "Referer": "https://www.mytvsuper.com/",
        "Sec-CH-UA": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }

    params = {
        "epg_platform": "web",
        "country_code": "HK",
        "network_code": network_code,
        "from": formatted_current_date,
        "to": formatted_date_after_seven_days,
    }

    response = requests.get("https://content-api.mytvsuper.com/v1/epg",
                            params=params, headers=headers, proxies=PROXIES)
    if response.status_code == 200:
        logger.info(response.url)
        data = response.json()

        total_epg = []

        for day_data in data:
            for item in day_data['item']:
                epgs = item['epg']
                for epg in epgs:
                    total_epg.append(epg)

        epgResult = []

        for i, epg_program in enumerate(total_epg):
            # 解析节目开始时间
            start_time = datetime.strptime(epg_program['start_datetime'], "%Y-%m-%d %H:%M:%S")
            program_name = epg_program['programme_title_tc']
            program_description = epg_program['episode_synopsis_tc']

            # 计算结束时间，如果有下一个节目，则用下一个节目的开始时间
            if i < len(total_epg) - 1:
                next_epg = total_epg[i + 1]
                next_start_time = datetime.strptime(next_epg['start_datetime'], "%Y-%m-%d %H:%M:%S")
                end_time = next_start_time  # 当前节目的结束时间为下一个节目的开始时间
            else:
                # 如果是最后一个节目，可以设定一个默认的结束时间，比如加30分钟
                end_time = start_time + timedelta(minutes=30)

            eastern_eight = pytz.timezone('Asia/Shanghai')
            start_time_with_tz = eastern_eight.localize(start_time)
            end_time_with_tz = eastern_eight.localize(end_time)

            epgResult.append(
                {"channelName": channel_name, "programName": program_name, "description": program_description,
                 "start": start_time_with_tz, "end": end_time_with_tz
                 }
            )

        return epgResult


def utc8_to_utc(local_time: datetime):
    eastern_eight = pytz.timezone('Asia/Shanghai')
    local_time_with_tz = eastern_eight.localize(local_time)
    utc_time = local_time_with_tz.astimezone(pytz.utc)
    return utc_time
