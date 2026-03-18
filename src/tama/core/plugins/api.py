"""
Defines functions available as the public plugin API.
"""
import inspect
import functools
import logging
import re
import traceback
import os.path
from collections.abc import Callable

from .api_internal import *

__all__ = ["on_load", "command", "regex"]


def _log_exception(exc: Exception):
    # Highest frame in the stack trace
    suspect_frame = traceback.extract_tb(exc.__traceback__)[-1]
    file = os.path.split(suspect_frame.filename)[1]
    line = suspect_frame.lineno
    logging.getLogger(__name__).exception(
        f"Plugin {file}:{line} threw unhandled {type(exc).__name__}"
    )


def _wrap_kwargs(f: Callable) -> Callable:
    sig = inspect.signature(f)

    if inspect.iscoroutinefunction(f):
        @functools.wraps(f)
        async def wrapper(*args, **kwargs) -> str | None:
            w_kwargs = {
                k: v for k, v in kwargs.items() if k in sig.parameters.keys()
            }
            try:
                return await f(*args, **w_kwargs)
            except Exception as exc:
                _log_exception(exc)
                # Swallow the exception after printing
                return "Error!"
        return wrapper

    else:
        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> str | None:
            w_kwargs = {
                k: v for k, v in kwargs.items() if k in sig.parameters.keys()
            }
            try:
                return f(*args, **w_kwargs)
            except Exception as exc:
                _log_exception(exc)
                # Swallow the exception after printing
                return "Error!"
        return wrapper



def on_load():
    def decorator(f: OnLoad.Executor):
        # No exception wrapper as these should be propagated to inform the bot
        # the plugin load failed
        setattr(
            f,
            "_tama_action",
            OnLoad(f),
        )
        return f
    return decorator


def command(
    name: str = None,
    *aliases: str,
    permissions: list[str] = None,
    blocking: bool = False,
):
    def decorator(f: Command.Executor):
        wrapper = _wrap_kwargs(f)
        setattr(
            wrapper,
            "_tama_action",
            Command(
                wrapper,
                name or f.__name__,
                [*aliases],
                f.__doc__.split("\n")[0].strip() if f.__doc__ is not None else None,
                permissions,
                blocking,
            ),
        )
        return wrapper
    return decorator


def regex(pattern: str | re.Pattern):
    def decorator(f: Regex.Executor):
        wrapper = _wrap_kwargs(f)
        setattr(
            wrapper,
            "_tama_action",
            Regex(wrapper, pattern)
        )
        return wrapper
    return decorator
