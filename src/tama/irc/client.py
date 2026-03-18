"""
Handles the interpretation of parsed IRC messages and converts them to an
observable event stream.
"""
import asyncio as aio
from collections import deque
from time import time
from logging import Logger, getLogger

from tama.config import ServerConfig
from tama.event import EventBus
from tama.irc.stream import IRCStream, IRCMessage

from .event import *


class IRCClient:
    __slots__ = (
        "name", "startup_config", "version", "stream", "bus",
        "nickname", "username", "realname",
        "_channel_list",
        "logger_name", "logger",
        "_starting_up", "_shutting_down", "_inbound_queue", "_outbound_queue",
        "_on_register",
        "_waiting_for_pong",
    )

    # Client data
    name: str
    startup_config: ServerConfig
    version: str

    # Connection primitives
    stream: IRCStream
    bus: EventBus

    # User data
    nickname: str
    username: str
    realname: str

    # State keeping
    _channel_list: list[str]

    # Raw IRC protocol logger
    logger_name: str
    logger: Logger

    # Internals
    _starting_up: bool
    _shutting_down: bool
    _inbound_queue: deque[IRCMessage]
    _outbound_queue: "aio.Queue[IRCMessage]"
    # Actions to perform once the IRC connection is registered.
    # These are not immediately queued on create as the connection is not
    # registered yet.
    _on_register: deque[IRCMessage]
    # Handles wait for server PONG
    _waiting_for_pong: str | None

    def __init__(
        self, name: str, startup_config: ServerConfig, stream: IRCStream
    ) -> None:
        self.name = name
        self.startup_config = startup_config
        # Import on runtime to not run into a circular import
        from tama import __version__ as version
        self.version = version

        self.stream = stream
        self.bus = EventBus(accept=[
            InvitedEvent,
            BotJoinedEvent, ChannelJoinedEvent,
            BotPartedEvent, ChannelPartedEvent,
            BotKickedEvent, ChannelKickedEvent,
            MessagedEvent, ActionEvent, NoticedEvent,
            ClosedEvent,
        ])

        self._starting_up = True
        self._shutting_down = False
        self._inbound_queue = deque()
        self._outbound_queue = aio.Queue()
        self._on_register = deque()
        self._waiting_for_pong = None

        self.nickname = startup_config.nick
        self.username = startup_config.user
        self.realname = startup_config.realname

        self._channel_list = []

        self.logger_name = f"tama.server.{name}.raw"
        self.logger = getLogger(self.logger_name)

    @classmethod
    async def create(cls, name: str, config: ServerConfig) -> "IRCClient":
        if config.port.startswith("+"):
            secure = True
            port = int(config.port)
        else:
            secure = False
            port = int(config.port)
        stream = await IRCStream.create(config.host, port, secure)
        obj = cls(name, config, stream)
        obj.nick(config.nick)
        obj.user(config.user, config.realname)
        if config.service_auth:
            cmd = config.service_auth.command or "IDENTIFY "
            if config.service_auth.username:
                cmd += config.service_auth.username + " "
            cmd += config.service_auth.password
            obj._on_register.append(IRCMessage(
                command="PRIVMSG",
                middle=(config.service_auth.service or "NickServ",),
                trailing=cmd,
            ))
        if config.channels:
            obj._on_register.extend([IRCMessage(
                command="JOIN",
                middle=(chan,)
            ) for chan in config.channels])
        return obj

    @classmethod
    async def create_after(
        cls, name: str, config: ServerConfig, seconds: int
    ) -> "IRCClient":
        await aio.sleep(seconds)
        return await cls.create(name, config)

    async def run(self) -> tuple[str, ServerConfig]:
        inbound = aio.create_task(self._inbound())
        outbound = aio.create_task(self._outbound())
        timeout = aio.create_task(self._timeout())
        while not self._shutting_down:
            done, pending = await aio.wait(
                [inbound, outbound, timeout], return_when=aio.FIRST_COMPLETED
            )
            # Getting the result from the future will raise exceptions
            if inbound in done:
                inbound.result()
                inbound = aio.create_task(self._inbound())
            if outbound in done:
                outbound.result()
                outbound = aio.create_task(self._outbound())
            # Cancel timeout future if not done
            if timeout not in done:
                timeout.cancel()
            else:
                timeout.result()
            timeout = aio.create_task(self._timeout())
        # Entered shutdown state, which means the inbound queue reached EOF or
        # the connection has timed out.
        # Don't await any further because nothing can be sent/received anymore.
        inbound.cancel()
        outbound.cancel()
        timeout.cancel()
        # Return startup config when connection dies for easy reconnection
        return self.name, self.startup_config

    async def _inbound(self) -> None:
        # Block if we have nothing to process
        if len(self._inbound_queue) == 0:
            try:
                new_messages = await self.stream.read_messages()
            except ConnectionError:
                # Connection failed, shut down
                getLogger(__name__).exception("IRC connection error")
                self._shutting_down = True
                return
            # Connection done, shut down
            if new_messages is None:
                getLogger(__name__).info("IRC connection closed")
                self._shutting_down = True
                return
            # Queue parsed messages
            self._inbound_queue.extend(new_messages)

        msg = self._inbound_queue.popleft()
        self.logger.info(">> %s", msg.raw[:-2].decode("utf-8"))
        # NOTE: Due to the fact all IRC commands are uppercase we turn them
        # to lower for nicer function dispatching.
        srv_handler = getattr(
            self,
            "handle_server_" + msg.command.lower(),
            self.handle_server_default,
            )
        srv_handler(msg)

    async def _outbound(self) -> None:
        # Block until we have a new message to send
        msg = await self._outbound_queue.get()
        self.logger.info("<< %s", msg.raw[:-2].decode("utf-8"))
        try:
            await self.stream.send_message(msg)
        except ConnectionError:
            # Connection failed, shut down
            getLogger(__name__).exception("IRC connection error")
            self._shutting_down = True

    async def _timeout(self) -> None:
        # 30 second PING interval
        await aio.sleep(30)
        if self._waiting_for_pong:
            # If we timeout and already pinged, die
            getLogger(__name__).error("IRC connection timed out")
            self._shutting_down = True
        else:
            msg = str(int(time()))
            self.ping(msg)
            self._waiting_for_pong = msg

    # Upstream command handlers
    def handle_server_default(self, msg: IRCMessage) -> None:
        getLogger(__name__).debug("Unhandled IRC message: %s", msg.command)
        # Do nothing for unhandled commands
        return

    def handle_server_ping(self, msg: IRCMessage) -> None:
        self.pong(msg.trailing)

    def handle_server_pong(self, msg: IRCMessage) -> None:
        if self._waiting_for_pong and self._waiting_for_pong == msg.trailing:
            self._waiting_for_pong = None

    def handle_server_nick(self, msg: IRCMessage) -> None:
        who = msg.parse_prefix_as_user()
        if who.nick == self.nickname:
            self.nickname = msg.trailing

    def handle_server_privmsg(self, msg: IRCMessage) -> None:
        # CTCP messages require further processing
        if msg.ctcp is not None:
            srv_handler = getattr(
                self,
                "handle_server_ctcp_" + msg.ctcp.command.lower(),
                self.handle_server_ctcp_default,
            )
            srv_handler(msg)
            return

        # If command param is the client nick, set the user as the location
        who = msg.parse_prefix_as_user()
        where = msg.middle[0]
        if where == self.nickname:
            where = who.nick
        self.bus.broadcast(MessagedEvent(
            client=self,
            who=who,
            where=where,
            message=msg.trailing,
        ))

    def handle_server_notice(self, msg: IRCMessage) -> None:
        # If command param is the client nick, set the user as the location
        who = msg.parse_prefix_as_user()
        where = msg.middle[0]
        if where == self.nickname:
            where = who.nick
        self.bus.broadcast(NoticedEvent(
            client=self,
            who=who,
            where=where,
            message=msg.trailing,
        ))

    def handle_server_invite(self, msg: IRCMessage) -> None:
        self.bus.broadcast(InvitedEvent(
            client=self,
            who=msg.parse_prefix_as_user(),
            to=msg.trailing,
        ))

    def handle_server_join(self, msg: IRCMessage) -> None:
        who = msg.parse_prefix_as_user()
        if who.nick == self.nickname:
            self._channel_list.append(msg.trailing)
            self.bus.broadcast(BotJoinedEvent(
                client=self,
                channel=msg.trailing,
                who=who,
            ))
        else:
            self.bus.broadcast(ChannelJoinedEvent(
                client=self,
                channel=msg.trailing,
                who=who,
            ))

    def handle_server_part(self, msg: IRCMessage) -> None:
        who = msg.parse_prefix_as_user()
        if who.nick == self.nickname:
            try:
                self._channel_list.remove(msg.trailing)
            except ValueError:
                getLogger(__name__).error(
                    "Parted a channel that was never joined."
                )
            self.bus.broadcast(BotPartedEvent(
                client=self,
                channel=msg.middle[0],
                who=who,
                message=msg.trailing,
            ))
        else:
            self.bus.broadcast(ChannelPartedEvent(
                client=self,
                channel=msg.middle[0],
                who=who,
                message=msg.trailing,
            ))

    def handle_server_kick(self, msg: IRCMessage) -> None:
        who = msg.parse_prefix_as_user()
        chan, target, *_ = msg.middle
        if target == self.nickname:
            try:
                self._channel_list.remove(msg.trailing)
            except ValueError:
                getLogger(__name__).error(
                    "Kicked from a channel that was never joined."
                )
            self.bus.broadcast(BotKickedEvent(
                client=self,
                channel=chan,
                who=who,
                target=target,
                message=msg.trailing,
            ))
        else:
            self.bus.broadcast(ChannelKickedEvent(
                client=self,
                channel=chan,
                who=who,
                target=target,
                message=msg.trailing,
            ))

    def handle_server_error(self, msg: IRCMessage) -> None:
        self.bus.broadcast(ClosedEvent(
            client=self,
            message=msg.trailing,
        ))

    # CTCP handlers
    def handle_server_ctcp_default(self, msg: IRCMessage) -> None:
        getLogger(__name__).debug("Unhandled CTCP message: %s", msg.ctcp.command)
        # Do nothing for unhandled CTCP commands
        return

    # A bunch of these will always will be a direct PRIVMSG to a user
    def handle_server_ctcp_clientinfo(self, msg: IRCMessage) -> None:
        reply_to = msg.parse_prefix_as_user()
        self.ctcp(reply_to.nick, "CLIENTINFO", "ACTION CLIENTINFO VERSION")

    def handle_server_ctcp_version(self, msg: IRCMessage) -> None:
        reply_to = msg.parse_prefix_as_user()
        self.ctcp(reply_to.nick, "VERSION", f"tama {self.version}")

    def handle_server_ctcp_time(self, msg: IRCMessage) -> None:
        reply_to = msg.parse_prefix_as_user()
        self.ctcp(reply_to.nick, "VERSION", f"tama {self.version}")

    def handle_server_ctcp_action(self, msg: IRCMessage) -> None:
        who = msg.parse_prefix_as_user()
        where = msg.middle[0]
        if where == self.nickname:
            where = who.nick
        self.bus.broadcast(ActionEvent(
            client=self,
            who=who,
            where=where,
            message=msg.ctcp.text,
        ))

    # Upstream reply code handlers
    def handle_server_rpl_welcome(self, msg: IRCMessage) -> None:
        self._starting_up = False
        while self._on_register:
            m = self._on_register.popleft()
            self._outbound_queue.put_nowait(m)

    def handle_server_err_nicknameinuse(self, msg: IRCMessage) -> None:
        # If we are still starting up, then retry with an underscore
        if self._starting_up:
            self.nickname = self.nickname + "_"
            self.nick(self.nickname)

    # Command executors
    def user(self, username: str, realname: str) -> None:
        self._outbound_queue.put_nowait(IRCMessage(
            command="USER",
            middle=(username, "0", "*"),
            trailing=realname,
        ))

    def nick(self, nickname: str) -> None:
        self._outbound_queue.put_nowait(IRCMessage(
            command="NICK",
            trailing=nickname,
        ))

    def ping(self, payload: str) -> None:
        self._outbound_queue.put_nowait(IRCMessage(
            command="PING",
            trailing=payload,
        ))

    def pong(self, payload: str) -> None:
        self._outbound_queue.put_nowait(IRCMessage(
            command="PONG",
            trailing=payload,
        ))

    def join(self, channel: str) -> None:
        self._outbound_queue.put_nowait(IRCMessage(
            command="JOIN",
            middle=(channel,)
        ))

    def notice(self, target: str, message: str) -> None:
        self._outbound_queue.put_nowait(IRCMessage(
            command="NOTICE",
            middle=(target,),
            trailing=message,
        ))

    def privmsg(self, target: str, message: str) -> None:
        self._outbound_queue.put_nowait(IRCMessage(
            command="PRIVMSG",
            middle=(target,),
            trailing=message,
        ))

    def ctcp(self, target: str, command: str, message: str) -> None:
        self._outbound_queue.put_nowait(IRCMessage(
            command="PRIVMSG",
            middle=(target,),
            ctcp=IRCMessage.CTCP(command=command, text=message),
        ))

    def action(self, target: str, message: str) -> None:
        self.ctcp(target, "ACTION", message)

    def quit(self, reason: str) -> None:
        self._outbound_queue.put_nowait(IRCMessage(
            command="QUIT",
            trailing=reason,
        ))
