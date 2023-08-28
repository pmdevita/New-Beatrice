
ENCRYPT_MODES = ["xsalsa20_poly1305", "xsalsa20_poly1305_lite", "xsalsa20_poly1305_suffix"]


def select_mode(available_modes: list[str]) -> str:
    valid_modes = set(available_modes).intersection(set(ENCRYPT_MODES))
    return list(valid_modes)[0]

