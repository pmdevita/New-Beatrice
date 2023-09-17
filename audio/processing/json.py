import abc
import typing
from json import JSONDecodeError
try:
    import orjson
    pyjson = None

except ImportError:
    orjson = None
    import json as pyjson


class AbstractJSONWrapper(abc.ABC):
    JSONDecodeError = JSONDecodeError

    @staticmethod
    @abc.abstractmethod
    def dumps(data: typing.Any) -> bytes:
        raise NotImplemented

    @staticmethod
    @abc.abstractmethod
    def loads(data: str | bytes):
        raise NotImplemented


class PythonJSONWrapper(AbstractJSONWrapper):
    @staticmethod
    def loads(data: str | bytes):
        return pyjson.loads(data)

    @staticmethod
    def dumps(data: typing.Any) -> bytes:
        return pyjson.dumps(data).encode()


class OrJSONWrapper(AbstractJSONWrapper):
    @staticmethod
    def dumps(data: typing.Any) -> bytes:
        return orjson.dumps(data)

    @staticmethod
    def loads(data: str | bytes) -> typing.Any:
        return orjson.loads(data)


if orjson is not None:
    json = OrJSONWrapper
else:
    json = PythonJSONWrapper

