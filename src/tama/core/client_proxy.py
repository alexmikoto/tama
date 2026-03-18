from logging import Logger
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tama.irc import IRCClient

if TYPE_CHECKING:
    from tama.core.bot import TamaBot

__all__ = ["ClientProxy", "ClientContext"]


@dataclass
class ClientContext:
    channel: str
    reply_to: str


class ClientProxy:
    __slots__ = ("client", "bot", "ctx")

    client: IRCClient
    bot: "TamaBot"
    ctx: ClientContext

    def __init__(self, client: IRCClient, bot: "TamaBot", ctx: ClientContext = None) -> None:
        self.client = client
        self.bot = bot
        self.ctx = ctx

    def _get_irc_logger(self, target: str) -> Logger | None:
        # Very intimate access
        return self.bot._get_irc_logger(self.client, target)  # noqa

    @property
    def nickname(self) -> str:
        return self.client.nickname

    def join(self, channel: str):
        self.client.join(channel)

    def nick(self, nickname: str):
        self.client.nick(nickname)

    def message(self, message: str, target: str = None) -> None:
        if not target:
            if self.ctx:
                target = self.ctx.channel
            else:
                raise TypeError
        log = self._get_irc_logger(target)
        if log:
            log.info("<%s> %s", self.client.nickname, message)
        self.client.privmsg(target, message)

    def action(self, message: str, target: str = None) -> None:
        if not target:
            if self.ctx:
                target = self.ctx.channel
            else:
                raise TypeError
        log = self._get_irc_logger(target)
        if log:
            log.info("* %s %s", self.client.nickname, message)
        self.client.action(target, message)

    def notice(self, message: str, target: str = None) -> None:
        if not target:
            if self.ctx:
                target = self.ctx.reply_to
            else:
                raise TypeError
        log = self._get_irc_logger(target)
        if log:
            log.info("-%s- %s", self.client.nickname, message)
        self.client.notice(target, message)
