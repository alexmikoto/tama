from tama import api
from tama.util.irc import is_valid_nick

__all__ = ["nick", "join", "part", "say", "act", "message","quit_", "reload"]

special = "[]\\`_^{|}"


@api.command(permissions=["bot_control"])
async def nick(
    text: str, client: api.Client = None
) -> None:
    """<nick> - changes nick to <nick>"""
    new_nick, *other = text.strip().split(" ", 1)
    # Spaces are not allowed
    if len(other) > 0:
        client.notice("Invalid nickname")
        return
    # Check if nick is compliant with expected rules
    if not is_valid_nick(new_nick):
        client.notice("Invalid nickname")
        return
    client.notice(f"Attempting to change nickname to {new_nick}")
    client.nick(new_nick)


@api.command(permissions=["bot_control"])
async def join(
    text: str, client: api.Client = None
) -> None:
    """<channel> - joins <channel>"""
    channel, *other = text.strip().split(" ", 1)
    if len(other) > 0:
        client.notice("Invalid channel")
        return
    client.join(channel)


@api.command(permissions=["bot_control"])
async def part(
    text: str, client: api.Client = None
) -> None:
    """<channel> - parts from <channel>"""
    channel, *other = text.strip().split(" ", 1)
    if len(other) > 0:
        client.notice("Invalid channel")
        return
    if channel not in client.channel_list:
        client.notice("Not currently in channel")
        return
    client.part(channel)


@api.command(permissions=["bot_control"])
async def say(
    text: str, channel: str,
    client: api.Client = None
) -> None:
    """[<channel>] <text> - sends the given <text>, in <channel> if specified."""
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
async def act(
    text: str, channel: str,
    client: api.Client = None
) -> None:
    """[<channel>] <text> - acts out the given <text>, in <channel> if specified."""
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
async def message(
    text: str, client: api.Client = None
) -> None:
    """<target> <text> - sends an IRC message to <target> with <text>."""
    target, *msg = text.strip().split(" ", 1)
    if len(msg) == 0:
        client.notice("Empty message")
    client.message(msg[0], target)


@api.command(permissions=["bot_control"])
async def notice(
    text: str, client: api.Client = None
) -> None:
    """<target> <text> - sends an IRC notice to <target> with <text>."""
    target, *msg = text.strip().split(" ", 1)
    if len(msg) == 0:
        client.notice("Empty message")
    client.notice(msg[0], target)


@api.command("quit", permissions=["bot_control"], auto_help=False)
async def quit_(text: str, bot: api.Bot = None) -> None:
    """shuts down the bot."""
    reason = text.strip()
    bot.shutdown(reason)


@api.command(permissions=["bot_control"], auto_help=False)
async def reload(text: str, bot: api.Bot = None) -> None:
    """reloads the bot."""
    reason = text.strip()
    bot.reload(reason)
