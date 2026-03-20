"""
penis.py

This plugin has been ported directly from CloudBot, which is under the GPLv3
license.

All credit goes to the Cloudbot maintainers.
"""
import random

from tama import api

balls = ["(_)_)", "8", "B", "(___)__)", "(_)(_)", "(@)@)", "3"]
shaft = [
    "=",
    "==",
    "===",
    "====",
    "=====",
    "========",
    "/////////////////////////",
    "|||||||||||||",
    "\u2248\u2248\u2248",
]
head = ["D", "Q", ">", "|\u2283", "\u22d1", "\u22d9", "\u22d7"]
emission = ["~ ~ ~ ~", "~ * ~ &", "", "*~* *~* %"]
bodypart = [
    "face",
    "glasses",
    "thigh",
    "tummy",
    "back",
    "hiney",
    "hair",
    "boobs",
    "tongue",
]


@api.command("penis", "bepis", auto_help=False)
def penis(text: str, reply: api.Func) -> None:
    """[nick] - much dongs, very ween, add a user nick as an argument for slightly different 'output'"""
    if not text:
        reply(
            f"{random.choice(balls)}{random.choice(shaft)}{random.choice(head)}"
        )
    else:
        person = text.split(" ")[0]
        reply(
            f"{random.choice(balls)}{random.choice(shaft)}{random.choice(head)}{random.choice(emission)} all over {person}'s {random.choice(bodypart)}"
        )
