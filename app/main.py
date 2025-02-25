from xml.dom import minidom

from fastapi import FastAPI, Response

from app.db.crud.epg import get_channel_by_platform, get_recent_programs
from app.db.models.base import init_database
from app.epg.EpgGenerator import generateEpg
from app.epg_platform import MyTvSuper

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/tvb")
async def request_my_tv_super_epg():
    return await MyTvSuper.get_channels()


@app.get("/epg/{platform}")
async def request_epg_by_platform(platform: str):
    channels = await get_channel_by_platform(platform_name=platform)
    programs = await get_recent_programs(platform_name=platform)

    generate_channels = []
    generate_programs = []
    for channel in channels:
        generate_channels.append({"channelName": channel.name})

    print(generate_channels)

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

# @router.post("/platforms/")
# async def create_platform(name: str):
#     return await epg.create_platform(name)
#
# @router.post("/channels/")
# async def create_channel(platform_id: int, name: str, description: str):
#     return await epg.create_channel(platform_id, name, description)
#
# @router.post("/programs/")
# async def create_program(channel_id: int, name: str, description: str, start_time, end_time):
#     return await epg.create_program(channel_id, name, description, start_time, end_time)
