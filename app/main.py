import asyncio
import os
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Response, HTTPException, Query

from app.epg.EpgGenerator import generateEpg
from app.epg_platform import MyTvSuper, Hami

from loguru import logger
import xml.etree.ElementTree as ET

from app.epg_platform.NowTV import request_nowtv_today_epg

logger.add("runtime.log")

app = FastAPI(openapi_url=None, redoc_url=None)


@app.get("/")
async def root():
    return {"message": ""}


# 创建一个scheduler实例
scheduler = AsyncIOScheduler()


@scheduler.scheduled_job('interval', minutes=10)
async def cron_job():
    # 执行任务的内容，例如打印当前时间
    print(f"The current time is {datetime.now()}")
    await request_all_epg_job()


def mkdir_if_need(file_path):
    # 获取文件的目录
    directory = os.path.dirname(file_path)
    # 检查目录是否存在，如果不存在则创建目录
    if not os.path.exists(directory):
        os.makedirs(directory)  # 创建多层目录


async def request_my_tv_super_epg():
    file_path = get_epg_file_name_today("tvb")
    mkdir_if_need(file_path)
    if not os.path.exists(file_path):
        channels, programs = await MyTvSuper.get_channels(force=True)
        response_xml = await gen_channel(channels, programs)
        # 使用 with 语句打开文件，确保文件在操作完成后被正确关闭
        with open(file_path, "wb") as file:
            file.write(response_xml)
    else:
        print(f"今日mytvsuper epg已获取，不执行更新")
    # 删除旧的EPG
    delete_old_epg_file("tvb")


async def request_hami_epg():
    file_path = get_epg_file_name_today("hami")
    mkdir_if_need(file_path)
    if not os.path.exists(file_path):
        channels, programs = await Hami.request_all_epg()
        response_xml = await gen_channel(channels, programs)
        # 使用 with 语句打开文件，确保文件在操作完成后被正确关闭
        with open(file_path, "wb") as file:
            file.write(response_xml)
    else:
        print(f"今日hami epg已获取，不执行更新")
    # 删除旧的EPG
    delete_old_epg_file("hami")


async def request_now_tv_epg():
    file_path = get_epg_file_name_today("nowtv")
    mkdir_if_need(file_path)
    if not os.path.exists(file_path):
        response_xml = await request_nowtv_today_epg()
        # 使用 with 语句打开文件，确保文件在操作完成后被正确关闭
        with open(file_path, "wb") as file:
            file.write(response_xml)
    else:
        print(f"今日nowtv epg已获取，不执行更新")
    # 删除旧的EPG
    delete_old_epg_file("tvb")


def get_date_str():
    # 获取当前时间
    current_time = datetime.now()
    # 格式化当前时间为 YYYYMMDD
    formatted_time = current_time.strftime('%Y%m%d')
    return formatted_time


def get_epg_file_name_today(platform):
    """
    获取今天的epg文件名
    :param platform:
    :return:
    """
    current_directory = os.getcwd()
    epgDir = f'{current_directory}/epg_files/{platform}'
    return f'{epgDir}/{platform}_{get_date_str()}.xml'


def delete_old_epg_file(platform):
    """
    删除旧的EPG
    :param platform:
    :return:
    """
    current_directory = os.getcwd()
    epgDir = f'{current_directory}/epg_files/{platform}'
    todayFile = os.path.basename(get_epg_file_name_today(platform))  # 获取今天的文件名
    for file in os.listdir(epgDir):
        if file.endswith(".xml"):
            if file != todayFile:
                os.remove(os.path.join(epgDir, file))
                logger.info(f"删除旧的EPG：{file}")


@app.get("/epg/{platform}")
async def request_epg_by_platform(platform: str):
    filePath = get_epg_file_name_today(platform)
    if os.path.exists(filePath):
        with open(filePath, "rb") as file:  # 使用 'rb' 模式
            xml_bytes = file.read()  # 读取文件内容，返回 bytes
        return Response(content=xml_bytes, media_type="application/xml")
    else:
        raise HTTPException(status_code=404)


@app.get("/epg")
async def custom_aggregate_epg(platforms: str = Query(..., description="平台列表，用逗号分隔，按优先级排序")):
    """
    自定义聚合EPG数据

    platforms参数示例: ?platforms=tvb,nowtv,hami
    """
    # 分割平台列表
    platform_list = [p.strip() for p in platforms.split(',') if p.strip()]
    return await checkout_epg_multiple(platform_list)


@app.get("/all")
async def aggregate_epg():
    platform_list = ["tvb", "nowtv", "hami"]
    return await checkout_epg_multiple(platform_list)  # 按优先级排序的平台列表


async def checkout_epg_multiple(platform_list):
    merged_root = ET.Element("tv")
    merged_root.set("generator-info-name", "Charming Aggregate")

    channels_seen = set()  # 跟踪已处理的channel id

    for platform in platform_list:
        file_path = get_epg_file_name_today(platform)
        if not os.path.exists(file_path):
            continue

        with open(file_path, "rb") as file:
            xml_content = file.read()

        try:
            platform_root = ET.fromstring(xml_content)

            # 处理channels
            for channel in platform_root.findall("./channel"):
                channel_id = channel.get("id")
                if channel_id not in channels_seen:
                    channels_seen.add(channel_id)
                    merged_root.append(channel)

                    # 同时添加该频道的所有节目
                    for programme in platform_root.findall(f"./programme[@channel='{channel_id}']"):
                        merged_root.append(programme)

        except ET.ParseError as e:
            print(f"Error parsing XML for platform {platform}: {e}")
            continue

    if len(list(merged_root)) == 0:
        raise HTTPException(status_code=404, detail="No EPG data available")

    # 将合并后的XML转换回字符串
    merged_xml = ET.tostring(merged_root, encoding="utf-8", xml_declaration=True)
    return Response(content=merged_xml, media_type="application/xml")


async def gen_channel(channels, programs):
    return await generateEpg(channels, programs)


async def request_all_epg_job():
    tasks = [
        request_my_tv_super_epg(),
        request_now_tv_epg(),
        request_hami_epg()
    ]
    # 使用 asyncio.gather 来并发执行请求
    for task in tasks:
        try:
            await task
        except Exception as e:
            # 处理异常，记录错误日志或其他处理方式
            logger.error(f"请求EPG时发生错误: {str(e)}")


@app.on_event("startup")
async def startup():
    logger.info("定时任务启动")
    scheduler.start()
    await request_all_epg_job()
