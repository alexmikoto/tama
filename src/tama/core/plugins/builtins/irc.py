from tama import api, TamaBot

__all__ = ["nick", "join", "say", "act", "message","quit_", "reload"]


@api.command(permissions=["bot_control"])
def nick(
    text: str, sender: TamaBot.User = None, client: TamaBot.Client = None
) -> None:
    """<nick> - changes nick to <nick>"""
    new_nick, *other = text.strip().split(" ", 1)
    if len(other) > 0:
        client.notice(sender.nick, "Invalid nickname")
    client.nick(new_nick)


@api.command(permissions=["bot_control"])
def join(
    text: str, sender: TamaBot.User = None, client: TamaBot.Client = None
) -> None:
    """<channel> - joins <channel>"""
    channel, *other = text.strip().split(" ", 1)
    if len(other) > 0:
        client.notice(sender.nick, "Invalid channel")
    client.join(channel)


@api.command(permissions=["bot_control"])
def say(
    text: str, channel: str,
    sender: TamaBot.User = None, client: TamaBot.Client = None
) -> None:
    payload = text.strip()
    if payload.startswith("#"):
        channel, *msg = text.strip().split(" ", 1)
        if len(msg) == 0:
            client.notice(sender.nick, "Empty message")
        msg = msg[0]
    else:
        msg = text
    client.message(channel, msg)


@api.command(permissions=["bot_control"])
def act(
    text: str, channel: str,
    sender: TamaBot.User = None, client: TamaBot.Client = None
) -> None:
    payload = text.strip()
    if payload.startswith("#"):
        channel, *msg = text.strip().split(" ", 1)
        if len(msg) == 0:
            client.notice(sender.nick, "Empty action")
        msg = msg[0]
    else:
        msg = text
    client.action(channel, msg)


@api.command(permissions=["bot_control"])
def message(
    text: str, sender: TamaBot.User = None, client: TamaBot.Client = None
) -> None:
    target, *msg = text.strip().split(" ", 1)
    if len(msg) == 0:
        client.notice(sender.nick, "Empty message")
    client.message(target, msg[0])


@api.command(permissions=["bot_control"])
def notice(
    text: str, sender: TamaBot.User = None, client: TamaBot.Client = None
) -> None:
    target, *msg = text.strip().split(" ", 1)
    if len(msg) == 0:
        client.notice(sender.nick, "Empty message")
    client.notice(target, msg[0])


@api.command("quit", permissions=["bot_control"])
def quit_(text: str, bot: TamaBot = None) -> None:
    reason = text.strip()
    bot.shutdown(reason)


@api.command(permissions=["bot_control"])
def reload(text: str, bot: TamaBot = None) -> None:
    reason = text.strip()
    bot.reload(reason)
