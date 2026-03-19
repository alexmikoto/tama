from typing import TYPE_CHECKING
from dataclasses import dataclass

from tama.event import Event
from tama.irc.user import IRCUser

if TYPE_CHECKING:
    from tama.irc.client import IRCClient

__all__ = [
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


@dataclass
class WelcomeBurstEvent(Event):
    """
    IRC server welcome messages.
    """
    client: "IRCClient"
    message: str


@dataclass
class ModeChangeEvent(Event):
    """
    IRC modes changed for either a user or a channel.
    """
    client: "IRCClient"
    who: IRCUser
    target: str
    mode: str
    args: tuple[str, ...]


class BotModeChangeEvent(ModeChangeEvent):
    """
    Bot IRC modes changed.
    """


class ChannelModeChangeEvent(ModeChangeEvent):
    """
    Channel IRC modes changed.
    """


@dataclass
class NickChangeEvent(Event):
    """
    A user changed IRC nickname.
    """
    client: "IRCClient"
    who: IRCUser
    new_nick: str


@dataclass
class InvitedEvent(Event):
    """
    Received an invite to an IRC channel.
    """
    client: "IRCClient"
    who: IRCUser
    to: str


@dataclass
class JoinedEvent(Event):
    """
    Someone joined an IRC channel.
    """
    client: "IRCClient"
    channel: str
    who: IRCUser


@dataclass
class BotJoinedEvent(JoinedEvent):
    """
    Bot joined an IRC channel.
    """
    topic: str | None
    topic_by: str | None
    topic_at: str | None
    userlist: tuple[str, ...]


@dataclass
class ChannelJoinedEvent(JoinedEvent):
    """
    Another nickname joined an active IRC channel.
    """


@dataclass
class PartedEvent(Event):
    """
    Parted an IRC channel.
    """
    client: "IRCClient"
    channel: str
    who: IRCUser
    message: str


@dataclass
class BotPartedEvent(PartedEvent):
    """
    Bot parted an IRC channel.
    """


@dataclass
class ChannelPartedEvent(PartedEvent):
    """
    Another nickname parted an active IRC channel.
    """


@dataclass
class KickedEvent(Event):
    """
    Kicked from an IRC channel.
    """
    client: "IRCClient"
    channel: str
    who: IRCUser
    target: str
    message: str


@dataclass
class BotKickedEvent(KickedEvent):
    """
    Bot was kicked from IRC channel.
    """


@dataclass
class ChannelKickedEvent(KickedEvent):
    """
    Another nickname was kicked from an active IRC channel.
    """


@dataclass
class MessagedEvent(Event):
    """
    Received an IRC message.
    """
    client: "IRCClient"
    who: IRCUser
    where: str
    message: str


@dataclass
class NoticedEvent(Event):
    """
    Received an IRC notice.
    """
    client: "IRCClient"
    who: IRCUser
    where: str
    message: str


@dataclass
class ActionEvent(Event):
    """
    Received a CTCP action message.
    """
    client: "IRCClient"
    who: IRCUser
    where: str
    message: str


@dataclass
class ClosedEvent(Event):
    """
    IRC connection will be closed
    """
    client: "IRCClient"
    message: str


@dataclass
class UserQuitEvent(Event):
    """
    Another user quit the IRC server.
    """
    client: "IRCClient"
    who: IRCUser
    message: str
