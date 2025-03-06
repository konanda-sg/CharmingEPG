import html
import re
import xml.etree.ElementTree as ET

import pytz


async def generateEpg(channels, programs):
    tv = ET.Element("tv",
                    {"generator-info-name": "Charming"})

    for channel in channels:
        channelName: str = channel["channelName"]
        # 创建 channel 元素
        channel = ET.SubElement(tv, "channel", id=channelName)
        display_name = ET.SubElement(channel, "display-name", lang="zh")
        display_name.text = channelName

    data_list = []
    for programs in programs:
        channelName: str = programs["channelName"]
        start_time = time_stamp_to_timezone_str(programs["start"])
        end_time = time_stamp_to_timezone_str(programs["end"])
        programme = ET.SubElement(tv, "programme", channel=channelName, start=start_time, stop=end_time)
        title = ET.SubElement(programme, "title", lang="zh")
        title.text = programs["programName"]
        if programs["description"]:
            description_str = programs["description"]
            description_str = clean_invalid_xml_chars(description_str)
            description_str = html.escape(description_str)
            data_list.append(description_str)
            description = ET.SubElement(programme, "desc", lang="zh")
            description.text = description_str

    xml_str = ET.tostring(tv, encoding='utf-8')
    return xml_str


def clean_invalid_xml_chars(text):
    # 使用正则表达式去除无效字符
    return re.sub(r'[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]', '', text)


def time_stamp_to_timezone_str(timestamp_s):
    target_tz = pytz.timezone('Asia/Shanghai')
    local_dt = timestamp_s.astimezone(target_tz)
    formatted_time = local_dt.strftime('%Y%m%d%H%M%S %z')
    return formatted_time
