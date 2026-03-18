from tama import api

__all__ = ["help_"]


@api.command("help", auto_help=False)
def help_(
    text: str,
    bot: api.Bot = None, client: api.Client = None
) -> None:
    """<command> - shows help for <command>"""
    command, *other = text.strip().split(" ", 1)
    if len(other) > 0:
        client.notice("Invalid command name")

    # Return a list of commands if none was specified
    if command == "":
        cmdlist = [cmd for cmd in bot.act_commands]
        client.notice(f"Available commands: {', '.join(cmdlist)}")
        return

    # Only exact matches
    try:
        command = bot.act_commands[command]
        if command.docstring:
            msg = bot.command_prefix + command.name + " " + command.docstring
        else:
            msg = bot.command_prefix + command.name + " - No help available"
        client.message(msg)
    except KeyError:
        client.notice("No such command")
