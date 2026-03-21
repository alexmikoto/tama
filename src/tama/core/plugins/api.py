"""
Defines functions available as the public plugin API.
"""
import inspect
import functools
import logging
import re
import traceback
import os.path
import asyncio as aio
from collections.abc import Callable
from typing import Any, TypeVar

from .api_internal import *

# Load symbols to present them for plugin modules
from tama.event import Event
from tama.core.bot import TamaBot
from tama.core.db import TamaDB
from tama.core.client_proxy import ClientProxy
from tama.irc.user import IRCUser

__all__ = [
    "Bot", "Client", "User", "DB", "Func",
    "on_load", "on_connect",
    "event", "command", "regex",
    "run_sync_function", "sleep",
]

Bot = TamaBot
Client = ClientProxy
User = IRCUser
DB = TamaDB

Func = Callable[[str], None]

convenience = dict(
    reply=("client", "message"),
    action=("client", "action"),
    notice=("client", "notice"),
)


def _log_exception(exc: Exception):
    # Highest frame in the stack trace
    suspect_frame = traceback.extract_tb(exc.__traceback__)[-1]
    file = os.path.split(suspect_frame.filename)[1]
    line = suspect_frame.lineno
    logging.getLogger(__name__).exception(
        f"Plugin {file}:{line} threw unhandled {type(exc).__name__}"
    )


def _add_convenience(kwargs: dict[str, Any]) -> dict[str, Any]:
    to_add = {}
    for name, value in convenience.items():
        owner, path = value
        f = getattr(kwargs.get(owner, {}), path)
        to_add[name] = f
    return {**kwargs, **to_add}


def _wrap_kwargs(
    f: Callable,
    inject_db: bool = True,
    inject_convenience: bool = True,
    catch_all: bool = True,
) -> Callable:
    sig = inspect.signature(f)

    if inspect.iscoroutinefunction(f):
        @functools.wraps(f)
        async def wrapper(*args, **kwargs) -> str | None:
            if inject_convenience:
                kwargs = _add_convenience(kwargs)
            w_kwargs = {
                k: v for k, v in kwargs.items() if k in sig.parameters.keys()
            }
            # Only used if connecting to DB
            conn: TamaDB.Conn | None = None
            try:
                # Add "db" handler to hide the transaction logic from plugins
                if inject_db and "db" in sig.parameters:
                    db: TamaDB = kwargs["database"]
                    conn = await db.connect()
                    w_kwargs["db"] = conn
                return await f(*args, **w_kwargs)
            except Exception as exc:
                _log_exception(exc)
                # Swallow the exception after printing
                if catch_all:
                    return "Error!"
                else:
                    raise exc
            finally:
                if inject_db and conn is not None:
                    await conn.close()
        return wrapper

    else:
        if "db" in sig.parameters:
            raise TypeError("DB client functions must be async")

        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> str | None:
            if inject_convenience:
                kwargs = _add_convenience(kwargs)
            w_kwargs = {
                k: v for k, v in kwargs.items() if k in sig.parameters.keys()
            }
            try:
                return f(*args, **w_kwargs)
            except Exception as exc:
                _log_exception(exc)
                # Swallow the exception after printing
                if catch_all:
                    return "Error!"
                else:
                    raise exc
        return wrapper


def on_load():
    def decorator(f: OnLoad.Executor):
        wrapper = _wrap_kwargs(f, inject_db=False, inject_convenience=False, catch_all=False)
        setattr(
            wrapper,
            magic_attr,
            OnLoad(wrapper),
        )
        return wrapper
    return decorator


def on_connect():
    def decorator(f: OnLoad.Executor):
        wrapper = _wrap_kwargs(f, inject_convenience=False, catch_all=False)
        setattr(
            wrapper,
            magic_attr,
            OnConnect(wrapper),
        )
        return wrapper
    return decorator


def event(events: list[type[Event]]):
    def decorator(f: OnEvent.Executor):
        wrapper = _wrap_kwargs(f)
        # Force all listeners to be async
        if not inspect.iscoroutinefunction(wrapper):
            async def async_wrapper(*args, **kwargs) -> None:
                return wrapper(*args, **kwargs)
            wrapper = async_wrapper

        setattr(
            wrapper,
            magic_attr,
            OnEvent(
                executor=wrapper,
                events=events
            ),
        )
        return wrapper
    return decorator


def command(
    name: str = None,
    *aliases: str,
    auto_help: bool = True,
    permissions: list[str] = None,
):
    def decorator(f: Command.Executor):
        wrapper = _wrap_kwargs(f)
        setattr(
            wrapper,
            magic_attr,
            Command(
                executor=wrapper,
                name=name or f.__name__,
                aliases=[*aliases],
                auto_help=auto_help,
                docstring=f.__doc__.split("\n")[0].strip() if f.__doc__ is not None else None,
                permissions=permissions,
            ),
        )
        return wrapper
    return decorator


def regex(pattern: str | re.Pattern):
    def decorator(f: Regex.Executor):
        wrapper = _wrap_kwargs(f)
        setattr(
            wrapper,
            magic_attr,
            Regex(executor=wrapper, pattern=pattern)
        )
        return wrapper
    return decorator


T = TypeVar("T")

async def run_sync_function(func: Callable[..., T], *args, **kwargs) -> T:
    skel = functools.partial(func, *args, **kwargs)
    res = await aio.get_running_loop().run_in_executor(None, skel)
    return res


sleep = aio.sleep
