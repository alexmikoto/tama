"""
attacks.py

This plugin has been ported directly from CloudBot, which is under the GPLv3
license.

All credit goes to the Cloudbot maintainers.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from enum import Enum, unique
from typing import Any

from tama import api
from tama.util.legacy import textgen

irc_nick_re = re.compile(r"[A-Za-z0-9^{}\[\]\-`_|\\]+")


@unique
class RespType(Enum):
    ACTION = 1
    MESSAGE = 2
    REPLY = 3


def is_nick_valid(nick: str) -> bool:
    return bool(irc_nick_re.fullmatch(nick))


def is_self(client: api.Client, target):
    """Checks if a string is "****self" or contains client nickname."""
    return bool(
        re.search(
            f"(^..?.?.?self|{re.escape(client.nickname)})",
            target, re.I
        )
    )


attack_data: dict[str, dict[str, Any]] = defaultdict(dict)


class BasicAttack:
    def __init__(
        self,
        name,
        doc,
        *commands,
        action=None,
        file=None,
        response=RespType.ACTION,
        require_target=True,
    ) -> None:
        self.name = name
        self.action = action or name
        self.doc = doc
        self.commands = commands or [name]
        if file is None:
            file = f"{name}.json"

        self.file = file
        self.response = response
        self.require_target = require_target


ATTACKS = (
    BasicAttack("lart", "<user> - LARTs <user>"),
    BasicAttack(
        "flirt",
        "<user> - flirts with <user>",
        "flirt",
        "sexup",
        "jackmeoff",
        action="flirt with",
        response=RespType.MESSAGE,
    ),
    BasicAttack("kill", "<user> - kills <user>", "kill", "end"),
    BasicAttack("slap", "<user> - Makes the bot slap <user>."),
    BasicAttack(
        "compliment",
        "<user> - Makes the bot compliment <user>.",
        response=RespType.MESSAGE,
    ),
    BasicAttack(
        "strax",
        "[user] - Generates a quote from Strax, optionally targeting [user]",
        action="attack",
        response=RespType.MESSAGE,
        require_target=False,
    ),
    BasicAttack(
        "nk",
        "- outputs a random North Korea propaganda slogan",
        action="target",
        response=RespType.MESSAGE,
        require_target=False,
    ),
    BasicAttack(
        "westworld",
        "- Westworld quotes",
        action="target",
        response=RespType.MESSAGE,
        require_target=False,
    ),
    BasicAttack("insult", "<user> - insults <user>", response=RespType.MESSAGE),
    BasicAttack(
        "present",
        "<user> - gives gift to <user>",
        "present",
        "gift",
        action="give a gift to",
    ),
    BasicAttack("spank", "<user> - Spanks <user>"),
    BasicAttack(
        "bdsm", "<user> - Just a little bit of kinky fun.", "bdsm", "dominate"
    ),
    BasicAttack("clinton", "<user> - Clinton a <user>"),
    BasicAttack("trump", "<user> - Trump a <user>"),
    BasicAttack("glomp", "<user> - glomps <user>"),
    BasicAttack("bite", "<user> - bites <user>"),
    BasicAttack(
        "lurve",
        "<user> - lurves <user>",
        "lurve",
        "luff",
        "luv",
        response=RespType.MESSAGE,
    ),
    BasicAttack("hug", "<user> - hugs <user>", response=RespType.MESSAGE),
    BasicAttack(
        "highfive",
        "<user> - highfives <user>",
        "high5",
        "hi5",
        "highfive",
        response=RespType.MESSAGE,
    ),
    BasicAttack(
        "fight",
        "<user> - fights <user>",
        "fight",
        "fite",
        "spar",
        "challenge",
        response=RespType.MESSAGE,
    ),
    BasicAttack(
        "pokemon",
        "<user> - uses a pok\xe9mon on <user>",
        response=RespType.MESSAGE,
    ),
    BasicAttack(
        "stab", "<user> - stabs <user> in a random body part with random weapon"
    ),
)


def load_data(path, data_dict) -> None:
    data_dict.clear()
    with path.open(encoding="utf-8") as f:
        data_dict.update(json.load(f))


@api.on_load()
def load_attacks(bot: api.Bot = None) -> None:
    attack_data.clear()
    data_dir = bot.data_path / "attacks"
    for data_file in ATTACKS:
        load_data(data_dir / data_file.file, attack_data[data_file.name])


def basic_format(nick, text, data, **kwargs):
    user = text
    kwargs["user"] = user
    kwargs["target"] = user
    kwargs["nick"] = nick

    if text:
        try:
            templates = data["target_templates"]
        except KeyError:
            templates = data["templates"]
    else:
        templates = data["templates"]

    generator = textgen.TextGenerator(
        templates, data.get("parts", {}), variables=kwargs
    )

    return generator.generate_string()


def basic_attack(attack):
    async def func(text, client: api.Client = None, sender: api.User = None):
        nick = sender.nick
        responses = {
            RespType.ACTION: client.action,
            RespType.REPLY: client.message,
            RespType.MESSAGE: client.message,
        }

        target = text
        if target:
            if not is_nick_valid(target):
                return f"I can't {attack.action} that."

            if is_self(client, target):
                target = sender.nick
                nick = client.nickname

        out = basic_format(nick, target, attack_data[attack.name])

        responses[attack.response](out)
        return None

    func.__name__ = attack.name
    func.__doc__ = attack.doc
    return func


def create_basic_hooks() -> None:
    for attack in ATTACKS:
        globals()[attack.name] = api.command(
            *attack.commands, auto_help=attack.require_target
        )(basic_attack(attack))


create_basic_hooks()
