from tama import api
from string import ascii_letters, digits

__all__ = ["nick", "join", "say", "act", "message","quit_", "reload"]

special = "[]\\`_^{|}"


@api.command(permissions=["bot_control"])
def nick(
    text: str, client: api.Client = None
) -> None:
    """<nick> - changes nick to <nick>"""
    new_nick, *other = text.strip().split(" ", 1)
    # Spaces are not allowed
    if len(other) > 0:
        client.notice("Invalid nickname")
        return
    # Leading character has different rules, see: RFC2812
    if new_nick[0] not in ascii_letters + special:
        client.notice("Invalid nickname")
        return
    # Also see: RFC2812
    allowed_chars = ascii_letters + digits + special + "-"
    if any(c not in allowed_chars for c in new_nick[1:]):
        client.notice("Invalid nickname")
        return
    client.nick(new_nick)


@api.command(permissions=["bot_control"])
def join(
    text: str, client: api.Client = None
) -> None:
    """<channel> - joins <channel>"""
    channel, *other = text.strip().split(" ", 1)
    if len(other) > 0:
        client.notice("Invalid channel")
        return
    client.join(channel)


@api.command(permissions=["bot_control"])
def say(
    text: str, channel: str,
    client: api.Client = None
) -> None:
    payload = text.strip()
    if payload.startswith("#"):
        channel, *msg = text.strip().split(" ", 1)
        if len(msg) == 0:
            client.notice("Empty message")
            return
        msg = msg[0]
    else:
        msg = text
    client.message(msg, channel)


@api.command(permissions=["bot_control"])
def act(
    text: str, channel: str,
    client: api.Client = None
) -> None:
    payload = text.strip()
    if payload.startswith("#"):
        channel, *msg = text.strip().split(" ", 1)
        if len(msg) == 0:
            client.notice("Empty action")
        msg = msg[0]
    else:
        msg = text
    client.action(msg, channel)


@api.command(permissions=["bot_control"])
def message(
    text: str, client: api.Client = None
) -> None:
    target, *msg = text.strip().split(" ", 1)
    if len(msg) == 0:
        client.notice("Empty message")
    client.message(msg[0], target)


@api.command(permissions=["bot_control"])
def notice(
    text: str, client: api.Client = None
) -> None:
    target, *msg = text.strip().split(" ", 1)
    if len(msg) == 0:
        client.notice("Empty message")
    client.notice(msg[0], target)


@api.command("quit", permissions=["bot_control"])
def quit_(text: str, bot: api.Bot = None) -> None:
    reason = text.strip()
    bot.shutdown(reason)


@api.command(permissions=["bot_control"])
def reload(text: str, bot: api.Bot = None) -> None:
    reason = text.strip()
    bot.reload(reason)
