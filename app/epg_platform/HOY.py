import xml.etree.ElementTree as ET
from datetime import datetime
import pytz
import requests


def parse_epg_xml(xml_content, channel_name):
    root = ET.fromstring(xml_content)

    # UTC+8的日期（0点0分0秒）
    shanghai_tz = pytz.timezone('Asia/Shanghai')
    today = datetime.now(shanghai_tz).replace(hour=0, minute=0, second=0, microsecond=0)

    result = []

    for channel in root.findall('./Channel'):
        for epg_item in channel.findall('./EpgItem'):
            start_time_str = epg_item.find('./EpgStartDateTime').text
            end_time_str = epg_item.find('./EpgEndDateTime').text

            # 解析开始和结束时间，并设置为上海时区
            start_time = shanghai_tz.localize(datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S"))
            end_time = shanghai_tz.localize(datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S"))

            # 检查是否是今天或之后的节目
            if start_time.date() >= today.date():
                # 获取节目信息
                episode_info = epg_item.find('./EpisodeInfo')
                short_desc = episode_info.find('./EpisodeShortDescription').text
                episode_index = episode_info.find('./EpisodeIndex').text

                # 构建节目名称
                program_name = short_desc
                if int(episode_index) > 0:
                    program_name += f" 第{episode_index}集"

                # 构建输出项
                item = {
                    "channelName": channel_name,
                    "programName": program_name,
                    "description": "",
                    "start": start_time,
                    "end": end_time
                }

                result.append(item)

    return result


async def get_hoy_lists():
    url = "https://api2.hoy.tv/api/v3/a/channel"
    response = requests.get(url)
    channel_list = []
    if response.status_code == 200:
        data = response.json()
        if data['code'] == 200:
            for raw_channel in data['data']:
                channel_list.append(
                    {"channelName": raw_channel.get('name').get('zh_hk'),
                     "rawEpg": raw_channel.get('epg'),
                     "logo": raw_channel.get('logo')}
                )
            return channel_list
    return None


async def get_hoy_epg():
    channel_list = await get_hoy_lists()
    programme_list = []
    for channel in channel_list:
        url = channel['rawEpg']
        channel_name = channel['channelName']
        response = requests.get(url)
        if response.status_code == 200:
            programme_list.extend(parse_epg_xml(response.text, channel_name))
    return channel_list, programme_list

# 参考数据：
# {
#   "code": 200,
#   "data": [
#     {
#       "id": 1,
#       "name": {
#         "zh_hk": "HOY 國際財經台",
#         "en": "HOY IBC"
#       },
#       "videos": {
#         "id": 76,
#         "channel_type": "NORMAL"
#       },
#       "default_channel": false,
#       "synopsis": {
#         "zh_hk": "\r\n"
#       },
#       "image": "https://storage.hoy.tv/v1/image/channel/1.jpg",
#       "epg": "https://epg-file.hoy.tv/hoy/OTT7620250617.xml",
#       "orientation": "landscape"
#     },
#     {
#       "id": 2,
#       "name": {
#         "zh_hk": "HOY TV",
#         "en": "HOY TV"
#       },
#       "videos": {
#         "id": 77,
#         "channel_type": "NORMAL"
#       },
#       "default_channel": true,
#       "synopsis": {
#         "zh_hk": ""
#       },
#       "image": "https://storage.hoy.tv/v1/image/channel/2.jpg",
#       "epg": "https://epg-file.hoy.tv/hoy/OTT7720250617.xml",
#       "orientation": "landscape"
#     },
#     {
#       "id": 3,
#       "name": {
#         "zh_hk": "HOY 資訊台",
#         "en": "HOY Infotainment"
#       },
#       "videos": {
#         "id": 78,
#         "channel_type": "NORMAL"
#       },
#       "default_channel": false,
#       "synopsis": {
#         "zh_hk": ""
#       },
#       "image": "https://storage.hoy.tv/v1/image/channel/3.jpg",
#       "epg": "https://epg-file.hoy.tv/hoy/OTT7820250617.xml",
#       "orientation": "landscape"
#     }
#   ]
# }
