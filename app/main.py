import asyncio

from fastapi import FastAPI, Response

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
    async def process_channels():
        channels, programs = await MyTvSuper.get_channels(force=True)
        response_xml = await gen_channel(channels, programs)
        file_path = "mytvsuper.xml"

        # 使用 with 语句打开文件，确保文件在操作完成后被正确关闭
        with open(file_path, "wb") as file:
            file.write(response_xml)

    asyncio.create_task(process_channels())

    return {"result": "running"}


@app.get("/epg/{platform}")
async def request_epg_by_platform(platform: str):
    with open(platform, "rb") as file:  # 使用 'rb' 模式
        xml_bytes = file.read()  # 读取文件内容，返回 bytes
        return Response(content=xml_bytes, media_type="application/xml")


async def gen_channel(channels, programs):
    return await generateEpg(channels, programs)

# @app.on_event("startup")
# async def startup():
#     await init_database()
#     await MyTvSuper.get_channels()
