from logging import Logger
from typing import TYPE_CHECKING

from tama.irc import IRCClient

if TYPE_CHECKING:
    from tama.core.bot import TamaBot

__all__ = ["ClientProxy"]


class ClientProxy:
    __slots__ = ("client", "bot")

    client: IRCClient
    bot: "TamaBot"

    def __init__(self, client: IRCClient, bot: "TamaBot"):
        self.client = client
        self.bot = bot

    def _get_irc_logger(self, target: str) -> Logger | None:
        # Very intimate access
        return self.bot._get_irc_logger(self.client, target)  # noqa

    def join(self, channel: str):
        self.client.join(channel)

    def message(self, target: str, message: str) -> None:
        log = self._get_irc_logger(target)
        if log:
            log.info("<%s> %s", self.client.nickname, message)
        self.client.privmsg(target, message)

    def action(self, target: str, message: str) -> None:
        log = self._get_irc_logger(target)
        if log:
            log.info("* %s %s", self.client.nickname, message)
        self.client.action(target, message)

    def notice(self, target: str, message: str) -> None:
        log = self._get_irc_logger(target)
        if log:
            log.info("-%s- %s", self.client.nickname, message)
        self.client.notice(target, message)
