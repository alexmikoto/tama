"""
Defines the plugin API internals.
"""
import re
import inspect
from collections.abc import Callable
from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from tama.core.bot import TamaBot
    from tama.core.plugins.plugin import Plugin

__all__ = ["Action", "OnLoad", "Command", "Regex"]


class Action:
    is_async: bool
    executor: Any | None
    async_executor: Any | None

    # This is a weak reference
    parent_plugin: Callable[[], "Plugin"] | None

    def __init__(self, executor: Any):
        if inspect.iscoroutinefunction(executor):
            self.is_async = True
            self.executor = None
            self.async_executor = executor
        else:
            self.is_async = False
            self.executor = executor
            self.async_executor = None


class OnLoad(Action):
    class Executor(Protocol):
        def __call__(
            self,
            *,
            config: dict = None,
        ) -> None: ...

    def __init__(
        self,
        executor: "Loader.Executor",
    ):
        super().__init__(executor)


class Command(Action):
    name: str
    aliases: list[str]
    docstring: str | None
    executor: "Command.Executor | None"
    async_executor: "Command.AsyncExecutor | None"
    permissions: list[str] | None
    blocking: bool

    __slots__ = (
        "name", "aliases", "docstring", "executor", "async_executor",
        "permissions", "blocking",
    )

    class Executor(Protocol):
        def __call__(
            self,
            text: str,
            *,
            channel: str = None,
            sender: "TamaBot.User" = None,
            bot: "TamaBot" = None,
            client: "TamaBot.Client" = None,
        ) -> str | None: ...

    class AsyncExecutor(Protocol):
        async def __call__(
            self,
            text: str,
            *,
            channel: str = None,
            sender: "TamaBot.User" = None,
            bot: "TamaBot" = None,
            client: "TamaBot.Client" = None,
        ) -> str | None: ...

    def __init__(
        self,
        executor: "Command.Executor | Command.AsyncExecutor",
        name: str,
        aliases: list[str] | None = None,
        docstring: str | None = None,
        permissions: list[str] | None = None,
        blocking: bool = False,
    ):
        super().__init__(executor)
        self.name = name
        self.aliases = aliases
        self.docstring = docstring
        self.permissions = permissions
        self.blocking = blocking


class Regex(Action):
    pattern: re.Pattern
    executor: "Regex.Executor | None"
    async_executor: "Regex.AsyncExecutor | None"

    class Executor(Protocol):
        def __call__(
            self,
            match: re.Match,
            *,
            channel: str = None,
            sender: "TamaBot.User" = None,
            bot: "TamaBot" = None,
            client: "TamaBot.Client" = None,
        ) -> str | None: ...

    class AsyncExecutor(Protocol):
        async def __call__(
            self,
            match: re.Match,
            *,
            channel: str = None,
            sender: "TamaBot.User" = None,
            bot: "TamaBot" = None,
            client: "TamaBot.Client" = None,
        ) -> str | None: ...

    def __init__(
        self,
        executor: "Regex.Executor | Regex.AsyncExecutor",
        pattern: str | re.Pattern,
    ):
        super().__init__(executor)
        if not isinstance(pattern, re.Pattern):
            self.pattern = re.compile(pattern)
        else:
            self.pattern = pattern
