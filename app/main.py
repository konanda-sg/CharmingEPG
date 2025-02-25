from xml.dom import minidom

from fastapi import FastAPI, Response

from app.db.crud.epg import get_channel_by_platform, get_recent_programs
from app.db.models.base import init_database
from app.epg.EpgGenerator import generateEpg
from app.epg_platform import MyTvSuper
from loguru import logger

logger.add("runtime.log")

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/update/tvb")
async def request_my_tv_super_epg():
    return await MyTvSuper.get_channels(force=True)


@app.get("/epg/{platform}")
async def request_epg_by_platform(platform: str):
    logger.info(f"正在拉取平台:【{platform}】的本地EPG")
    channels = await get_channel_by_platform(platform_name=platform)
    programs = await get_recent_programs(platform_name=platform)

    generate_channels = []
    generate_programs = []
    for channel in channels:
        generate_channels.append({"channelName": channel.name})

    for program in programs:
        generate_programs.append(
            {"channelName": program.channel.name,
             "start": program.start_time,
             "end": program.end_time,
             "programName": program.name,
             "description": program.description})

    response_xml: str = await generateEpg(generate_channels, generate_programs)
    xml_doc = minidom.parseString(response_xml)
    formatted_xml = xml_doc.toprettyxml(indent="  ")
    # print(formatted_xml)
    return Response(content=formatted_xml, media_type="application/xml")


@app.on_event("startup")
async def startup():
    await init_database()
    await MyTvSuper.get_channels()
