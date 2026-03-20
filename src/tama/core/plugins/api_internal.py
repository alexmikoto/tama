"""
Defines the plugin API internals.
"""
import re
import inspect
from collections.abc import Callable
from typing import Any, Protocol, Awaitable, TYPE_CHECKING

from tama.event import Event

if TYPE_CHECKING:
    from tama.core.bot import TamaBot
    from tama.core.db import TamaDB
    from tama.core.plugins.plugin import Plugin

__all__ = [
    "magic_attr", "Action", "OnLoad", "EventSubscriber", "Command", "Regex"
]

# Attribute name to recognize metadata blocks in decorators
magic_attr = "_tama_action"


class Action:
    is_async: bool
    executor: Any | None

    # This is a weak reference
    parent_plugin: Callable[[], "Plugin"] | None

    def __init__(self, executor: Any):
        if inspect.iscoroutinefunction(executor):
            self.is_async = True
        else:
            self.is_async = False
        self.executor = executor


class OnLoad(Action):
    class Executor(Protocol):
        def __call__(
            self,
            *,
            config: dict = None,
            bot: "TamaBot" = None,
        ) -> None: ...

    def __init__(
        self,
        executor: "OnLoad.Executor",
    ):
        super().__init__(executor)


class EventSubscriber(Action):
    events: list[type[Event]]

    class Executor(Protocol):
        def __call__(
            self,
            *,
            event: Event = None,
            bot: "TamaBot" = None,
            client: "TamaBot.Client" = None,
            database: "TamaDB" = None,
        ) -> None: ...

    def __init__(
        self,
        executor: "EventSubscriber.Executor",
        events: list[type[Event]],
    ):
        super().__init__(executor)
        self.events = events


class Command(Action):
    name: str
    aliases: list[str]
    auto_help: bool
    docstring: str | None
    executor: "Command.Executor | None"
    permissions: list[str] | None

    __slots__ = (
        "name", "aliases", "auto_help", "docstring", "executor",
        "async_executor", "permissions"
    )

    class Executor(Protocol):
        def __call__(
            self,
            *,
            # Caller-provided parameters
            text: str = None,
            channel: str = None,
            sender: "TamaBot.User" = None,
            bot: "TamaBot" = None,
            client: "TamaBot.Client" = None,
            database: "TamaDB" = None,
            # Convenience methods
            reply: "Callable[[str], None]" = None,
            action: "Callable[[str], None]" = None,
            notice: "Callable[[str], None]" = None,
            db: "TamaDB.Conn" = None,
        ) -> str | Awaitable[str] | None: ...

    def __init__(
        self,
        executor: "Command.Executor",
        name: str,
        aliases: list[str] | None = None,
        auto_help: bool = True,
        docstring: str | None = None,
        permissions: list[str] | None = None,
    ):
        super().__init__(executor)
        self.name = name
        self.aliases = aliases
        self.auto_help = auto_help
        self.docstring = docstring
        self.permissions = permissions


class Regex(Action):
    pattern: re.Pattern
    executor: "Regex.Executor | None"

    __slots__ = ("pattern", "executor", "async_executor")

    class Executor(Protocol):
        def __call__(
            self,
            *,
            # Caller-provided parameters
            match: re.Match = None,
            channel: str = None,
            sender: "TamaBot.User" = None,
            bot: "TamaBot" = None,
            client: "TamaBot.Client" = None,
            database: "TamaDB" = None,
            # Convenience methods
            reply: "Callable[[str], None]" = None,
            action: "Callable[[str], None]" = None,
            notice: "Callable[[str], None]" = None,
            db: "TamaDB.Conn" = None,
        ) -> str | Awaitable[str] | None: ...

    def __init__(
        self,
        executor: "Regex.Executor",
        pattern: str | re.Pattern,
    ):
        super().__init__(executor)
        if not isinstance(pattern, re.Pattern):
            self.pattern = re.compile(pattern)
        else:
            self.pattern = pattern
