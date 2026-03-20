from string import ascii_letters, digits

__all__ = ["is_valid_nick"]

special = "[]\\`_^{|}"

allowed_leading = ascii_letters + special
allowed_chars = ascii_letters + digits + special + "-"


def is_valid_nick(nick: str) -> bool:
    # Disallow empty nickname
    if len(nick) < 1:
        return False
    # Leading character has different rules, see: RFC2812
    if nick[0] not in allowed_leading:
        return False
    # Also see: RFC2812
    if any(c not in allowed_chars for c in nick[1:]):
        return False
    return True
