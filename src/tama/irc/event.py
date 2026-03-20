from typing import TYPE_CHECKING
from dataclasses import dataclass

from tama.event import Event
from tama.irc.user import IRCUser

if TYPE_CHECKING:
    from tama.irc.client import IRCClient

__all__ = [
    "IRCEvent",
    "WelcomeBurstEvent",
    "BotModeChangeEvent", "ChannelModeChangeEvent",
    "NickChangeEvent",
    "InvitedEvent",
    "JoinedEvent", "BotJoinedEvent", "ChannelJoinedEvent",
    "PartedEvent", "BotPartedEvent", "ChannelPartedEvent",
    "KickedEvent", "BotKickedEvent", "ChannelKickedEvent",
    "MessagedEvent", "NoticedEvent", "ActionEvent",
    "ClosedEvent", "UserQuitEvent",
]


@dataclass(frozen=True)
class IRCEvent(Event):
    """
    Any event created by the IRC client.
    """
    client: "IRCClient"


@dataclass(frozen=True)
class WelcomeBurstEvent(IRCEvent):
    """
    IRC server welcome messages.
    """
    message: str


@dataclass(frozen=True)
class ModeChangeEvent(IRCEvent):
    """
    IRC modes changed for either a user or a channel.
    """
    who: IRCUser
    target: str
    mode: str
    args: tuple[str, ...]


@dataclass(frozen=True)
class BotModeChangeEvent(ModeChangeEvent):
    """
    Bot IRC modes changed.
    """


@dataclass(frozen=True)
class ChannelModeChangeEvent(ModeChangeEvent):
    """
    Channel IRC modes changed.
    """


@dataclass(frozen=True)
class NickChangeEvent(IRCEvent):
    """
    A user changed IRC nickname.
    """
    who: IRCUser
    new_nick: str


@dataclass(frozen=True)
class InvitedEvent(IRCEvent):
    """
    Received an invite to an IRC channel.
    """
    who: IRCUser
    to: str


@dataclass(frozen=True)
class JoinedEvent(IRCEvent):
    """
    Someone joined an IRC channel.
    """
    channel: str
    who: IRCUser


@dataclass(frozen=True)
class BotJoinedEvent(JoinedEvent):
    """
    Bot joined an IRC channel.
    """
    topic: str | None
    topic_by: str | None
    topic_at: str | None
    userlist: tuple[str, ...]


@dataclass(frozen=True)
class ChannelJoinedEvent(JoinedEvent):
    """
    Another nickname joined an active IRC channel.
    """


@dataclass(frozen=True)
class PartedEvent(IRCEvent):
    """
    Parted an IRC channel.
    """
    channel: str
    who: IRCUser
    message: str


@dataclass(frozen=True)
class BotPartedEvent(PartedEvent):
    """
    Bot parted an IRC channel.
    """


@dataclass(frozen=True)
class ChannelPartedEvent(PartedEvent):
    """
    Another nickname parted an active IRC channel.
    """


@dataclass(frozen=True)
class KickedEvent(IRCEvent):
    """
    Kicked from an IRC channel.
    """
    channel: str
    who: IRCUser
    target: str
    message: str


@dataclass(frozen=True)
class BotKickedEvent(KickedEvent):
    """
    Bot was kicked from IRC channel.
    """


@dataclass(frozen=True)
class ChannelKickedEvent(KickedEvent):
    """
    Another nickname was kicked from an active IRC channel.
    """


@dataclass(frozen=True)
class MessagedEvent(IRCEvent):
    """
    Received an IRC message.
    """
    who: IRCUser
    where: str
    message: str


@dataclass(frozen=True)
class NoticedEvent(IRCEvent):
    """
    Received an IRC notice.
    """
    who: IRCUser
    where: str
    message: str


@dataclass(frozen=True)
class ActionEvent(IRCEvent):
    """
    Received a CTCP action message.
    """
    who: IRCUser
    where: str
    message: str


@dataclass(frozen=True)
class ClosedEvent(IRCEvent):
    """
    IRC connection will be closed
    """
    message: str


@dataclass(frozen=True)
class UserQuitEvent(IRCEvent):
    """
    Another user quit the IRC server.
    """
    who: IRCUser
    message: str
