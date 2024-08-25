import logging
import struct
from typing import Protocol
from libnacl import crypto_aead_xchacha20poly1305_ietf_encrypt, crypto_aead_aes256gcm_encrypt  # type: ignore

ENCRYPT_MODES = ["aead_aes256_gcm_rtpsize", "aead_xchacha20_poly1305_rtpsize"]
MAX_UINT32 = 4294967295


def select_mode(available_modes: list[str]) -> str:
    valid_modes = set(available_modes).intersection(set(ENCRYPT_MODES))
    return list(valid_modes)[0]


class NaclAeadAlgorithm(Protocol):
    def __call__(self, message: bytes, aad: bytes, nonce: bytes, key: bytes) -> bytes:
        ...


class AudioEncryption:
    algorithm: NaclAeadAlgorithm

    def __init__(self, secret_key: bytes, mode: str) -> None:
        self.nonce = 0
        self.secret_key = secret_key
        self.mode = mode
        logging.info(f"Using mode {mode}")
        match mode:
            case "aead_aes256_gcm_rtpsize":
                self.algorithm = crypto_aead_aes256gcm_encrypt
            case "aead_xchacha20_poly1305_rtpsize":
                self.algorithm = crypto_aead_xchacha20poly1305_ietf_encrypt
            case _:
                raise Exception(f"Unknown encryption mode {mode}")

    def encrypt(self, aad: bytes, nonce: bytes, message: bytes) -> bytes:
        return self.algorithm(message, aad, nonce, self.secret_key)

    def get_nonce(self) -> int:
        nonce = self.nonce
        self.nonce += 1
        if self.nonce > MAX_UINT32:
            self.nonce = 0
        return nonce

    def __call__(self, header: bytearray, data: bytes) -> bytes:
        # With thanks to BetterDisco by elderlabs
        if self.mode == "aead_aes256_gcm_rtpsize":
            nonce = bytearray(12)
        else:
            nonce = bytearray(24)
        struct.pack_into('>I', nonce, 0, self.get_nonce())
        ciphertext = self.encrypt(bytes(header), bytes(nonce), data)
        return header + ciphertext + nonce[:4]
