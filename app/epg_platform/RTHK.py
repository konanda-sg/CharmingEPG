import json

import requests
from bs4 import BeautifulSoup
import datetime
import pytz
from datetime import datetime, timedelta

from loguru import logger

rthk_channels = [
    {"channelName": "RTHK31", "channelId": "tv31"},
    {"channelName": "RTHK32", "channelId": "tv32"},
    {"channelName": "RTHK33", "channelId": "tv33"},
    {"channelName": "RTHK34", "channelId": "tv34"},
    {"channelName": "RTHK35", "channelId": "tv35"},
]


def parse_epg_from_html(html_content, channel_name):
    soup = BeautifulSoup(html_content, 'html.parser')

    # 今天的日期
    today = datetime.now().strftime("%Y%m%d")

    # 查找所有日期块
    date_blocks = soup.find_all('div', class_='slideBlock')

    results = []

    for block in date_blocks:
        date_str = block.get('date')

        # 只处理今天及以后的日期
        if date_str >= today:
            # 解析日期
            year = int(date_str[0:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])

            # 该日期下的所有节目
            programs = block.find_all('div', class_='shdBlock')

            for program in programs:
                # 获取时间
                time_block = program.find('div', class_='shTimeBlock')
                time_elements = time_block.find_all('p', class_='timeDis')

                start_time_str = time_elements[0].text.strip()
                end_time_str = time_elements[2].text.strip() if len(time_elements) > 2 else None

                start_hour, start_min = map(int, start_time_str.split(':'))

                # 开始时间
                start_datetime = datetime(year, month, day, start_hour, start_min)
                start_datetime = pytz.timezone('Asia/Shanghai').localize(start_datetime)

                # 结束时间
                if end_time_str:
                    end_hour, end_min = map(int, end_time_str.split(':'))
                    end_datetime = datetime(year, month, day, end_hour, end_min)

                    # 如果结束时间小于开始时间，说明跨天了
                    if end_hour < start_hour or (end_hour == start_hour and end_min < start_min):
                        end_datetime += timedelta(days=1)

                    end_datetime = pytz.timezone('Asia/Shanghai').localize(end_datetime)
                else:
                    # 如果没有结束时间，默认为30分钟后
                    end_datetime = start_datetime + timedelta(minutes=30)

                # 节目名称
                title_block = program.find('div', class_='shTitle')
                program_name = title_block.find('a').text.strip()

                # 节目详情
                sub_title_block = program.find('div', class_='shSubTitle')
                description = sub_title_block.find('a').text.strip() if sub_title_block and sub_title_block.find(
                    'a') else ""

                # 导出
                epg_entry = {
                    "channelName": channel_name,
                    "programName": program_name,
                    "description": description,
                    "start": start_datetime,
                    "end": end_datetime
                }

                results.append(epg_entry)

    return results


async def get_rthk_epg():
    programme_list = []
    try:
        for channel in rthk_channels:
            url = f"https://www.rthk.hk/timetable/{channel['channelId']}"
            logger.info(f"【RTHK】：正在请求{url}")
            response = requests.get(url)
            if response.status_code == 200:
                epg_list = parse_epg_from_html(response.text, channel["channelName"])
                programme_list.extend(epg_list)
    except Exception as e:
        logger.error(f"Error requesting EPG for {channel['channelName']}: {e}")
    return rthk_channels, programme_list
