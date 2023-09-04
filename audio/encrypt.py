import nacl.secret
import nacl.utils

ENCRYPT_MODES = ["xsalsa20_poly1305", "xsalsa20_poly1305_suffix"]
#  "xsalsa20_poly1305_lite", "xsalsa20_poly1305_suffix",


def select_mode(available_modes: list[str]) -> str:
    valid_modes = set(available_modes).intersection(set(ENCRYPT_MODES))
    return list(valid_modes)[0]


# With help from Discord.py
def encrypt_audio(mode: str, secret_key: bytes, header: bytearray, data: bytes) -> bytes:
    box = nacl.secret.SecretBox(secret_key)

    match mode:
        case "xsalsa20_poly1305":
            n = bytearray(24)
            n[:12] = header
            nonce = bytes(n)
            result = header + box.encrypt(data, bytes(nonce)).ciphertext
        case "xsalsa20_poly1305_suffix":
            nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
            result = header + box.encrypt(data, bytes(nonce)).ciphertext + nonce
        case _:
            raise Exception(f"Unknown encryption mode \"{mode}\"")

    return result



