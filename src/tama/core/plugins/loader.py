import os
import sys
import importlib
import importlib.util
from logging import getLogger
from typing import TYPE_CHECKING

from .plugin import Plugin

if TYPE_CHECKING:
    from tama.core.bot import TamaBot

__all__ = ["load_builtins", "load_plugins"]


def load_builtins() -> list[Plugin]:
    builtin_pkg = "tama.core.plugins.builtins"
    builtins = importlib.import_module(builtin_pkg)
    return [
        Plugin(
            f"{builtin_pkg}.{module_name}",
            importlib.import_module(f"{builtin_pkg}.{module_name}")
        )
        for module_name in builtins.__all__
    ]


def load_plugins(path: str, bot: "TamaBot" = None, config: dict[str, dict] = None) -> list[Plugin]:
    py_files = [
        f for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f)) and f.endswith(".py")
    ]
    plugins = []
    for py in py_files:
        try:
            module_name = py[:-3]
            module_classname = f"tama.plugins.{py[:-3]}"
            module_config = config[module_name] if config is not None and config.get(module_name) is not None else {}
            spec = importlib.util.spec_from_file_location(
                module_classname, os.path.join(path, py)
            )
            if spec is None:
                # Shit broke somehow
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_classname] = module
            spec.loader.exec_module(module)
            getLogger(__name__).info(f"Plugin {py} loaded.")
            p = Plugin(module_classname, module)
            p.on_load(bot=bot, config=module_config)
            plugins.append(p)
        except SyntaxError:
            getLogger(__name__).error(f"Plugin {py} malformed.")
        except Exception as exc:  # noqa
            getLogger(__name__).exception(f"Error while loading plugin {py}:")

    return plugins
