import os
import sys
import importlib
import importlib.util
from logging import getLogger

from .plugin import Plugin

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


def load_plugins(path: str) -> list[Plugin]:
    py_files = [
        f for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f)) and f.endswith(".py")
    ]
    plugins = []
    for py in py_files:
        try:
            module_name = py[:-3]
            module_classname = f"tama.plugins.{py[:-3]}"
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
            plugins.append(p)
        except SyntaxError:
            getLogger(__name__).error(f"Plugin {py} malformed.")
        except Exception as exc:  # noqa
            getLogger(__name__).exception(f"Error while loading plugin {py}:")

    return plugins
