# app/db/crud/epg.py
from datetime import datetime, timedelta

from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.db.models.epg import Platform, Channel, Program


async def create_platform(name: str):
    try:
        platform = await Platform.create(name=name)
        return platform
    except IntegrityError:
        return None  # 如果发生重复，返回 None


async def create_channel(platform_name: str, channel_name: str):
    async with in_transaction():
        platform = await Platform.get(name=platform_name)
        channel = await Channel.get_or_none(name=channel_name, platform=platform)
        if channel:
            return channel  # 不再调用 update_or_create
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
    # 使用 select_related 来减少查询次数
    channels = await Channel.filter(platform=platform).select_related('platform')
    return channels


async def is_latest_program_by_platform_name_over_6h(platform_name: str):
    # 查询对应的 Platform
    platform = await Platform.filter(name=platform_name).first()

    if not platform:
        # 如果没有找到 Platform，返回 True
        return True

    # 查询该 Platform 下的最新 Program
    # 使用 values 只获取必要的字段
    latest_program = await Program.filter(channel__platform=platform).order_by('-updated_at').values(
        'updated_at').first()

    if not latest_program:
        # 如果没有找到 Program，返回 True
        return True

    # 获取当前时间
    current_time = datetime.utcnow()

    # 检查 latest_program 的 updated_at 是否超过 6 小时
    return (current_time - latest_program.updated_at) > timedelta(hours=6)


async def get_recent_programs(platform_name: str):
    platform = await Platform.get(name=platform_name)
    # 使用 select_related 来减少查询次数
    programs = await Program.filter(
        channel__platform_id=platform.id,
    ).select_related('channel', 'channel__platform').all()

    return programs
