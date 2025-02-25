# app/db/crud/epg.py

from tortoise.exceptions import IntegrityError

from app.db.models.epg import Platform, Channel, Program


async def create_platform(name: str):
    try:
        platform = await Platform.create(name=name)
        return platform
    except IntegrityError:
        return None  # 如果发生重复，返回 None


async def create_channel(platform_name: str, channel_name: str):
    platform = await Platform.get(name=platform_name)
    channel = await Channel.get_or_none(name=channel_name, platform=platform)
    if channel:
        return await channel.update_or_create(platform=platform, name=channel_name)
    else:
        return await Channel.create(platform=platform, name=channel_name)


async def delete_programs_by_channel(platform_name: str, channel_name: str):
    platform = await Platform.get(name=platform_name)
    channel = await Channel.get_or_none(name=channel_name, platform=platform)
    delete_count = await Program.filter(channel=channel).delete()
    return delete_count


async def create_program(platform_name: str, channel_name: str, program_name: str, description: str, start_time,
                         end_time):
    platform = await Platform.get(name=platform_name)
    channel = await Channel.get_or_none(name=channel_name, platform=platform)
    return await Program.update_or_create(channel=channel, name=program_name, description=description,
                                          start_time=start_time,
                                          end_time=end_time)


async def get_channel_by_platform(platform_name: str):
    platform = await Platform.get(name=platform_name)
    channels = await Channel.filter(platform=platform)
    return channels


async def get_recent_programs(platform_name: str):
    platform = await Platform.get(name=platform_name)
    # 查询指定平台的频道和相关的节目
    programs = await Program.filter(
        channel__platform_id=platform.id,
    ).prefetch_related('channel').all()

    return programs
