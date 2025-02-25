from tortoise.models import Model
from tortoise import fields


class Platform(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, unique=True)  # 添加 unique=True 约束
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Channel(Model):
    id = fields.IntField(pk=True)
    platform = fields.ForeignKeyField('models.Platform', related_name='channels')
    name = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Program(Model):
    id = fields.IntField(pk=True)
    channel = fields.ForeignKeyField('models.Channel', related_name='programs')
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    start_time = fields.DatetimeField()
    end_time = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
