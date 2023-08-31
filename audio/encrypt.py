import nacl.secret


ENCRYPT_MODES = ["xsalsa20_poly1305", "xsalsa20_poly1305_lite", "xsalsa20_poly1305_suffix"]


def select_mode(available_modes: list[str]) -> str:
    valid_modes = set(available_modes).intersection(set(ENCRYPT_MODES))
    return list(valid_modes)[0]


# With help from Discord.py
def encrypt_audio(secret_key: bytes, header: bytes, data: bytes) -> bytes:
    box = nacl.secret.SecretBox(secret_key)


