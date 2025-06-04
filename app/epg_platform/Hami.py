import asyncio

import pytz
import requests
from datetime import datetime, timedelta
from loguru import logger

UA = "HamiVideo/7.12.806(Android 11;GM1910) OKHTTP/3.12.2"
headers = {
    'X-ClientSupport-UserProfile': '1',
    'User-Agent': UA
}


async def request_channel_list():
    params = {
        "appVersion": "7.12.806",
        "deviceType": "1",
        "appOS": "android",
        "menuId": "162"
    }

    url = "https://apl-hamivideo.cdn.hinet.net/HamiVideo/getUILayoutById.php"
    channel_list = []
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        elements = []

        # 分类有点多，要找到是专门频道列表的分类
        for info in data["UIInfo"]:
            if info["title"] == "頻道一覽":
                elements = info['elements']
                break
        for element in elements:
            channel_list.append({"channelName": element['title'], "contentPk": element['contentPk']})
    return channel_list


async def get_programs_with_retry(channel):
    max_retries = 5
    retries = 0

    while retries < max_retries:
        try:
            programs = await request_epg(channel['channelName'], channel['contentPk'])
            return programs
        except Exception as e:
            retries += 1
            logger.error(f"Error requesting EPG for {channel['channelName']}: {e}")
            logger.info(f"Retry {retries}/{max_retries} after 30 seconds...")

            if retries < max_retries:
                await asyncio.sleep(30)  # 等待30秒再重试
            else:
                logger.info(f"Max retries reached for {channel['channelName']}, skipping...")
                return []  # 达到最大重试次数后返回空列表


async def request_all_epg():
    rawChannels = await request_channel_list()
    rawPrograms = []
    for channel in rawChannels:
        programs = await get_programs_with_retry(channel)
        if len(programs) > 0:
            rawPrograms.extend(programs)
    return rawChannels, rawPrograms


async def request_epg(channel_name: str, content_pk: str):
    url = "https://apl-hamivideo.cdn.hinet.net/HamiVideo/getEpgByContentIdAndDate.php"
    logger.info("正在生成EPG：" + content_pk + "," + channel_name)
    epgResult = []
    for i in range(7):
        date = datetime.now() + timedelta(days=i)
        formatted_date = date.strftime('%Y-%m-%d')
        params = {
            "deviceType": "1",
            "Date": formatted_date,
            "contentPk": content_pk,
        }
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if len(data['UIInfo'][0]['elements']) > 0:
                for element in data['UIInfo'][0]['elements']:
                    if len(element['programInfo']) > 0:
                        program_info = element['programInfo'][0]
                        start_time_with_tz, end_time_with_tz = hami_time_to_datetime(program_info['hintSE'])
                        epgResult.append(
                            {"channelName": element['title'], "programName": program_info['programName'],
                             "description": "",
                             "start": start_time_with_tz, "end": end_time_with_tz
                             }
                        )

    return epgResult


def hami_time_to_datetime(time_range: str):
    # 解析时间字符串
    start_time_str, end_time_str = time_range.split('~')

    # 解析为datetime对象
    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")

    # 将无时区的datetime对象添加上海时区信息
    shanghai_tz = pytz.timezone('Asia/Shanghai')
    start_time_shanghai = shanghai_tz.localize(start_time)
    end_time_shanghai = shanghai_tz.localize(end_time)
    return start_time_shanghai, end_time_shanghai

# if __name__ == '__main__':
#     asyncio.run(request_epg("EUROSPORT","OTT_LIVE_0000001771"))
