"""

"""
import re
import asyncio as aio
import functools
import logging
import logging.handlers
from pathlib import Path

from tama.config import Config
from tama.util.trie import Trie
from tama.irc import IRCClient, IRCUser
from tama.irc.event import *

# Load plugins from private APIs so we can include this in the public API
from tama.core.plugins.plugin import *
from tama.core.plugins.api_internal import *
import tama.core.plugins.loader as loader

from .exit_status import ExitStatus
from .client_proxy import *
from .acl import ACL
from .exc import NameCollisionError

__all__ = ["TamaBot"]


class TamaBot:
    config: Config
    command_prefix: str
    log_folder: str
    log_raw: bool
    log_irc: bool

    plugin_folder: str
    data_folder: str

    clients: list[IRCClient]
    plugins: list[Plugin]

    # Registered actions
    act_commands: dict[str, Command]
    act_regex: list[Regex]

    act_commands_idx: Trie

    # Permissions manager
    acl: ACL

    # List of all event handlers provided
    event_handlers: list[tuple]

    # Enumeration for exit status
    ExitStatus = ExitStatus
    _exit_status: ExitStatus | None

    # Provide access to Client proxy and IRCUser here for a cleaner API
    Client = ClientProxy
    User = IRCUser

    def __init__(self, config: Config):
        self.config = config
        self.command_prefix = config.tama.prefix
        self.log_folder = config.tama.log_folder or "logs"
        # Bloody booleans
        self.log_raw = (
            config.tama.log_raw if config.tama.log_raw is not None else False
        )
        self.log_irc = (
            config.tama.log_irc if config.tama.log_irc is not None else True
        )
        # Set default paths for plugin and data files
        self.plugin_folder = (
            config.tama.plugin_folder if config.tama.plugin_folder else "plugins"
        )
        self.data_folder = (
            config.tama.data_folder if config.tama.data_folder else "data"
        )
        # Client bookkeeping
        self.clients = []
        # Load builtin plugins
        self.plugins = loader.load_builtins()
        # Load external plugins
        self.plugins.extend(
            loader.load_plugins(
                path=self.plugin_folder,
                bot=self,
                config=config.tama.plugins
            )
        )
        # For registered actions
        self.act_commands = {}
        self.act_regex = []
        self.act_commands_idx = Trie()
        # Only set exit status when exiting
        self._exit_status = None
        # Register plugin actions
        self._setup_plugins()
        # Load ACL
        self.acl = ACL(config.tama.permissions)
        # Populate list of event observers
        self.event_handlers = [
            (WelcomeBurstEvent, self.on_welcome_burst),
            (NickChangeEvent, self.on_nick_change),
            (InvitedEvent, self.on_invite),
            (BotJoinedEvent, self.on_join),
            (ChannelJoinedEvent, self.on_join),
            (BotPartedEvent, self.on_part),
            (ChannelPartedEvent, self.on_part),
            (BotKickedEvent, self.on_kick),
            (ChannelKickedEvent, self.on_kick),
            (MessagedEvent, self.on_message),
            (NoticedEvent, self.on_notice),
            (ActionEvent, self.on_action),
            (ClosedEvent, self.on_closed),
            (UserQuitEvent, self.on_user_quit)
        ]

    def connect(self, client: IRCClient):
        self.clients.append(client)
        self._subscribe_client_events(client)

        # Setup IRC logger and log connection startup
        log = self._get_irc_logger(client, client.name)
        if log:
            log.info(
                "-!- Connected to %s:%s",
                client.startup_config.host, client.startup_config.port
            )

    async def create_clients_from_config(self):
        for name, srv in self.config.server.items():
            client = await IRCClient.create(name, srv)
            self.connect(client)
            self._setup_client_raw_logger(client)

    def _setup_plugins(self):
        for plug in self.plugins:
            for act in plug.actions:
                if isinstance(act, Command):
                    if act.name in self.act_commands:
                        prev_act = self.act_commands[act.name]
                        raise NameCollisionError(
                            act.name,
                            prev_act.parent_plugin().module_name,
                            act.parent_plugin().module_name
                        )
                    self.act_commands[act.name] = act
                    self.act_commands_idx.add(act.name)
                elif isinstance(act, Regex):
                    self.act_regex.append(act)

        # Register aliases AFTER loading all commands, if there is any collision
        # drop a warning but do not raise the exception
        for plug in self.plugins:
            for act in plug.actions:
                if isinstance(act, Command):
                    for alias in act.aliases:
                        if alias in self.act_commands:
                            prev_act = self.act_commands[act.name]
                            exc = NameCollisionError(
                                act.name,
                                prev_act.parent_plugin().module_name,
                                act.parent_plugin().module_name
                            )
                            logging.getLogger(__name__).warning(exc.message)
                        else:
                            self.act_commands[alias] = act
                            self.act_commands_idx.add(alias)

    def _subscribe_client_events(self, client: IRCClient) -> None:
        for evt, handler in self.event_handlers:
            client.bus.subscribe(evt, handler)  # noqa

    def _unsubscribe_client_events(self, client: IRCClient) -> None:
        for evt, handler in self.event_handlers:
            client.bus.unsubscribe(evt, handler)  # noqa

    def _setup_client_raw_logger(self, client: IRCClient) -> None:
        if not self.log_raw:
            # Silence client logger
            client.logger.addHandler(logging.NullHandler())
            client.logger.propagate = False
            return

        log_dir = Path(self.log_folder)
        if not log_dir.is_dir():
            log_dir.mkdir(parents=True)

        hdl = logging.handlers.TimedRotatingFileHandler(
            filename=Path(self.log_folder, f"{client.name}.raw.log"),
            when="midnight",
            encoding="utf-8",
        )
        hdl.setFormatter(logging.Formatter(
            fmt=f"[{client.name}] [%(asctime)s] %(message)s",
            datefmt="%H:%M:%S"
        ))
        client.logger.addHandler(hdl)

    def _get_irc_logger(
        self, client: IRCClient, buffer: str
    ) -> logging.Logger | None:
        if not self.log_irc:
            return

        log_dir = Path(self.log_folder, client.name)
        if not log_dir.is_dir():
            log_dir.mkdir(parents=True)

        log = logging.getLogger(f"tama.server.{client.name}.irc.{buffer}")
        if len(log.handlers) == 0:
            hdl = logging.handlers.TimedRotatingFileHandler(
                filename=log_dir.joinpath(f"{buffer}.log"),
                when="midnight",
                encoding="utf-8",
            )
            hdl.setFormatter(logging.Formatter(
                fmt=f"[{client.name}:{buffer}] [%(asctime)s] %(message)s",
                datefmt="%H:%M:%S"
            ))
            log.addHandler(hdl)

        return log

    async def run(self) -> ExitStatus:
        done = set()
        pending = {
            aio.create_task(c.run()) for c in self.clients
        }
        while self._exit_status is None:
            for task in done:
                result = await task
                # We only get a client when we queued recreating a lost one
                if isinstance(result, IRCClient):
                    self.connect(result)
                    pending.add(aio.create_task(result.run()))
                # We get (name, config) when we lost a client
                elif isinstance(result, tuple):
                    name, cfg = result
                    pending.add(aio.create_task(IRCClient.create_after(
                        name, cfg, 5
                    )))
            done, pending = await aio.wait(
                pending, return_when=aio.FIRST_COMPLETED
            )

        if len(pending) > 0:
            await aio.wait(pending, return_when=aio.ALL_COMPLETED)

        return self._exit_status

    async def on_welcome_burst(self, evt: WelcomeBurstEvent) -> None:
        log = self._get_irc_logger(evt.client, evt.client.name)
        if log:
            log.info("%s", evt.message)

    async def on_nick_change(self, evt: NickChangeEvent) -> None:
        log = self._get_irc_logger(evt.client, evt.client.name)
        if log:
            log.info(
                "-!- %s is now known as %s",
                evt.who.nick, evt.new_nick
            )

    async def on_invite(self, evt: InvitedEvent) -> None:
        evt.client.join(evt.to)

    async def on_join(self, evt: BotJoinedEvent | ChannelJoinedEvent) -> None:
        log = self._get_irc_logger(evt.client, evt.channel)
        if log:
            log.info(
                "-!- %s (%s) has joined %s",
                evt.who.nick, evt.who.address, evt.channel,
            )

    async def on_part(self, evt: BotPartedEvent | ChannelPartedEvent) -> None:
        log = self._get_irc_logger(evt.client, evt.channel)
        if log:
            log.info(
                "-!- %s (%s) has left %s (%s)",
                evt.who.nick, evt.who.address, evt.channel, evt.message,
            )

    async def on_kick(self, evt: BotKickedEvent | ChannelKickedEvent) -> None:
        log = self._get_irc_logger(evt.client, evt.channel)
        if log:
            log.info(
                "-!- %s (%s) has kicked %s from %s (%s)",
                evt.who.nick, evt.who.address,
                evt.target, evt.channel, evt.message,
            )

    async def on_notice(self, evt: NoticedEvent) -> None:
        if evt.who.is_nil:
            where = evt.client.name
        else:
            where = evt.where
        log = self._get_irc_logger(evt.client, where)
        if log:
            if evt.who.is_nil:
                # Assume it's a server notice
                log.info("%s", evt.message)
            else:
                log.info("-%s- %s", evt.who.nick, evt.message)

    async def on_message(self, evt: MessagedEvent) -> None:
        # Log message before parsing
        log = self._get_irc_logger(evt.client, evt.where)
        if log:
            log.info("<%s> %s", evt.who.nick, evt.message)

        # Use ClientProxy for outbound stuff instead of the client directly
        client_proxy = ClientProxy(
            client=evt.client,
            bot=self,
            ctx=ClientContext(evt.where, evt.who.nick)
        )

        exec_kwargs = dict(
            channel=evt.where,
            sender=evt.who,
            bot=self,
            client=client_proxy
        )

        # Parse commands
        if evt.message.startswith(self.command_prefix):
            cmd, *text = evt.message.split(" ", 1)
            cmd = cmd[1:]
            if len(text) == 0:
                text = ""
            else:
                text = text[0]

            # Check for exact matches
            r = self.act_commands.get(cmd)

            if not r:
                # Check for non-exact matches
                cmd_match = self.act_commands_idx.search(cmd)
                if len(cmd_match) == 0:
                    return
                elif len(cmd_match) == 1:
                    r = self.act_commands.get(cmd_match[0])
                else:
                    dym = "Did you mean: " + cmd_match[0]
                    for m in cmd_match[1:-1]:
                        dym += ", " + m
                    dym += " or " + cmd_match[-1] + "?"
                    evt.client.notice(evt.who.nick, dym)
                    return

            # Validate permissions
            if r.permissions is not None:
                for p in r.permissions:
                    if not self.acl.check_permission(evt.who, p):
                        client_proxy.message(
                            f"{evt.who.nick}, you don't have permission to do that."
                        )
                        return

            # Check if the command allows empty queries
            if r.auto_help:
                if text.strip() == "":
                    reply = r.docstring or f"{r.name}: parameters required"
                    client_proxy.notice(reply)
                    return

            if r.is_async:
                result = await r.async_executor(text, **exec_kwargs)
            else:
                if r.blocking:
                    result = await aio.get_running_loop().run_in_executor(
                        None, functools.partial(r.executor, text, **exec_kwargs)
                    )
                else:
                    result = r.executor(text, **exec_kwargs)

            if result:
                client_proxy.message(f"{evt.who.nick}, {result}")

        # Run regexp parsers
        for r in self.act_regex:
            match = re.search(r.pattern, evt.message)
            if match:
                if r.is_async:
                    result = await r.async_executor(match, **exec_kwargs)
                else:
                    result = r.executor(match, **exec_kwargs)

                if result:
                    client_proxy.message(f"{evt.who.nick}, {result}")

    async def on_action(self, evt: ActionEvent) -> None:
        log = self._get_irc_logger(evt.client, evt.where)
        if log:
            log.info("* %s %s", evt.who.nick, evt.message)

        # Use ClientProxy for outbound stuff instead of the client directly
        client_proxy = ClientProxy(
            client=evt.client,
            bot=self,
            ctx=ClientContext(evt.where, evt.who.nick)
        )

        # Act back at people
        mentioned = evt.client.nickname in evt.message.split(" ")
        if mentioned:
            return_act = evt.message.replace(evt.client.nickname, evt.who.nick)
            client_proxy.action(return_act)

    async def on_closed(self, evt: ClosedEvent) -> None:
        log = self._get_irc_logger(evt.client, evt.client.name)
        if log:
            log.info("-!- Disconnected: %s", evt.message)

        # Stop listening for events as we are entering a shutdown state
        self._unsubscribe_client_events(evt.client)

    async def on_user_quit(self, evt: UserQuitEvent) -> None:
        log = self._get_irc_logger(evt.client, evt.client.name)
        if log:
            log.info(
                "-!- %s has quit (%s)",
                evt.who.nick, evt.message
            )

    def _quit_client(self, client: IRCClient, reason: str) -> None:
        log = self._get_irc_logger(client, client.name)
        if log:
            log.info("-!- %s has quit (%s)", client.nickname, reason)
        client.quit(reason)

    def shutdown(self, reason: str) -> None:
        self._exit_status = ExitStatus.QUIT
        for client in self.clients:
            self._quit_client(client, reason)

    def reload(self, reason: str) -> None:
        self._exit_status = ExitStatus.RELOAD
        for client in self.clients:
            self._quit_client(client, reason)
