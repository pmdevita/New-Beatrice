import json
import struct
import typing

# Todo: Replace JSON dumping with f-string templates?
# Technically is cheating but would be way faster

JSONType: typing.TypeAlias = dict[str, "JSONType"] | list["JSONType"] | str | int | float | bool | None


class DiscordJSONPacket(typing.TypedDict):
    op: int
    d: JSONType


class Opcode2Ready(typing.TypedDict):
    ssrc: str
    ip: str
    port: int
    modes: list[str]


def _opcode(obj: typing.Any) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=True)


def opcode_0_identify(guild_id: str, user_id: str, session_id: str, token: str) -> str:
    return _opcode({
        "op": 0,
        "d": {
            "server_id": guild_id,
            "user_id": user_id,
            "session_id": session_id,
            "token": token
        }
    })


def opcode_1_select(address: str, port: int, mode: str) -> str:
    return _opcode({
        "op": 1,
        "d": {
            "protocol": "udp",
            "data": {
                "address": address,
                "port": port,
                "mode": mode
            }
        }
    })


def opcode_5_speaking(ssrc: int, delay: int = 0, microphone: bool =True, soundshare: bool= False, priority: bool = False) -> str:
    speaking = 0
    if microphone:
        speaking += 1 << 0
    if soundshare:
        speaking += 1 << 1
    if priority:
        speaking += 1 << 2
    return _opcode({
        "op": speaking,
        "d": {
            "speaking": 5,
            "delay": 0,
            "ssrc": 1
        }
    })


def opcode_3_heartbeat(nonce: int) -> str:
    return _opcode({
        "op": 3,
        "d": nonce
    })


# Mostly copied from Discord.py, thank you Discord.py maintainers!

def request_ip(ssrc: int) -> bytes:
    packet = bytearray(74)
    struct.pack_into(">H", packet, 0, 1)
    struct.pack_into(">H", packet, 2, 70)
    struct.pack_into(">I", packet, 4, ssrc)
    return bytes(packet)


def get_ip_response(data: bytes) -> typing.Tuple[str, int]:
    ip_start = 8
    ip_end = data.index(0, ip_start)
    ip = data[ip_start:ip_end].decode("ascii")
    port = struct.unpack_from(">H", data, len(data) - 2)[0]
    return ip, port
