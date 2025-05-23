import json
import os
from datetime import datetime

import requests
from loguru import logger
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from dotenv import load_dotenv
import pytz

load_dotenv(verbose=True, override=True)

PROXY_HTTP = os.getenv("PROXY_HTTP", None)
PROXY_HTTPS = os.getenv("PROXY_HTTPS", None)
UA = os.getenv("UA",
               "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")

PROXIES = None

if PROXY_HTTP and PROXY_HTTPS:
    PROXIES = {
        "http": PROXY_HTTP,
        "https": PROXY_HTTP
    }

CHANNEL_LIST = []
CHANNEL_NUMS = []


def get_official_channel_list():
    url = 'https://nowplayer.now.com/channels'
    HEADER = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Referer': 'https://nowplayer.now.com/channels',
        'User-Agent': UA,
        'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,ar-EG;q=0.6,ar;q=0.5'
    }

    response = requests.get(url, headers=HEADER, cookies={'LANG': 'zh'})

    soup = BeautifulSoup(response.text, 'html.parser')
    channels = []

    # 找到所有channel项
    items = soup.find_all('div', class_='product-item')
    channel_nums = []
    for item in items:
        # 获取logo图片URL
        img_tag = item.find('img')
        logo = img_tag['src'] if img_tag else None

        # 获取频道名称
        name_tag = item.find('p', class_='img-name')
        name = name_tag.text if name_tag else None

        # 获取频道号
        channel_tag = item.find('p', class_='channel')
        channel_no = channel_tag.text.replace('CH', '') if channel_tag else None

        channels.append({
            'logo': logo,
            'name': name,
            'channelNo': channel_no
        })
        channel_nums.append(channel_no)
    CHANNEL_LIST.clear()
    CHANNEL_LIST.extend(channels)
    CHANNEL_NUMS.clear()
    CHANNEL_NUMS.extend(channel_nums)


async def request_nowtv_today_epg():
    get_official_channel_list()
    xml_str = await get_now_tv_guide_to_epg(CHANNEL_NUMS, "all")
    return xml_str


async def get_now_tv_guide_to_epg(channel_numbers, cache_keyword):
    current_date = datetime.now().date()
    cache_key = f"{current_date}_{cache_keyword}"

    epg7Day = await fetch_7day_epg(channel_numbers)
    channels = CHANNEL_LIST
    tv = ET.Element("tv", {"generator-info-name": "Charming"})

    for sportChannel in channel_numbers:
        channelName = find_channel_name(channels, "{0}".format(sportChannel))
        # 创建 channel 元素
        channel = ET.SubElement(tv, "channel", id=channelName)
        display_name = ET.SubElement(channel, "display-name", lang="zh")
        display_name.text = channelName

    for day in range(1, 7 + 1):
        epgArray = epg7Day[day]
        for index, epgChild in enumerate(epgArray):
            channelName = find_channel_name(channels, "{0}".format(channel_numbers[index]))
            for epgItem in epgChild:
                start_time = time_stamp_to_timezone_str(epgItem["start"] / 1000)
                end_time = time_stamp_to_timezone_str(epgItem["end"] / 1000)
                programme = ET.SubElement(tv, "programme", channel=channelName, start=start_time, stop=end_time)
                title = ET.SubElement(programme, "title", lang="zh")
                title.text = epgItem.get("name", "")
    # 转换为字符串并格式化
    xml_str = ET.tostring(tv, encoding='utf-8')
    return xml_str


def time_stamp_to_timezone_str(timestamp_s):
    utc_dt = datetime.fromtimestamp(timestamp_s, tz=pytz.UTC)
    target_tz = pytz.timezone('Asia/Shanghai')
    local_dt = utc_dt.astimezone(target_tz)
    formatted_time = local_dt.strftime('%Y%m%d%H%M%S %z')
    return formatted_time


def find_channel_name(channels, channel_no):
    for item in channels:
        if item["channelNo"] == channel_no:
            return item["name"]


async def fetch_7day_epg(channel_numbers):
    sport_epg_cache = {}
    MIN_DAY = 1
    MaxDay = 7
    HEADERS = {
        'Accept': 'text/plain, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Referer': 'https://nowplayer.now.com/tvguide',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': UA,
    }
    COOKIES = {
        'LANG': 'zh'
    }
    for day in range(MIN_DAY, MaxDay + 1):
        params = {
            'channelIdList[]': channel_numbers,
            'day': str(day),
        }
        response = requests.get(
            'https://nowplayer.now.com/tvguide/epglist',
            params=params,
            headers=HEADERS,
            cookies=COOKIES,
            proxies=PROXIES,
        )
        logger.info(f"url:{response.url} status:{response.status_code}")
        if response.status_code == 200:
            response_json = response.json()
            sport_epg_cache[day] = response.json()  # 假设返回 JSON 数据

    return sport_epg_cache
