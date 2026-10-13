"""Encode DynamoDB low-level items without monetary float conversions."""

from decimal import Decimal

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer


def encode(item: dict) -> dict:
    serializer = TypeSerializer()
    return {key: serializer.serialize(value) for key, value in item.items()}


def decode(item: dict) -> dict:
    deserializer = TypeDeserializer()
    result = {key: deserializer.deserialize(value) for key, value in item.items()}
    return {
        key: int(value) if isinstance(value, Decimal) else value for key, value in result.items()
    }
