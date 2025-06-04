import requests
import xml.etree.ElementTree as ET

async def get_cn_channels_epg():
    url = 'https://epg.pw/xmltv/epg_CN.xml'
    response = requests.get(url)
    if response.status_code == 200:
        # 解析XML并立即去除格式化
        root = ET.fromstring(response.text)
        unformatted_xml = ET.tostring(root, encoding='utf-8').decode('utf-8')
        return unformatted_xml
