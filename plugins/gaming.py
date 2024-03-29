"""
gaming.py

Dice, coins, and random generation for gaming. Ported from CloudBot.

Modified By:
    - Luke Rogers <https://github.com/lukeroge>
    - Alex108 <https://github.com/alex108>

License:
    GPL v3
"""
import random
import re

from tama import api


whitespace_re = re.compile(r'\s+')
valid_diceroll = re.compile(r'^([+-]?(?:\d+|\d*d(?:\d+|F))(?:[+-](?:\d+|\d*d(?:\d+|F)))*)( .+)?$', re.I)
sign_re = re.compile(r'[+-]?(?:\d*d)?(?:\d+|F)', re.I)
split_re = re.compile(r'([\d+-]*)d?(F|\d*)', re.I)


def n_rolls(count, n):
    """roll an n-sided die count times
    :type count: int
    :type n: int | str
    """
    if n == "F":
        return [random.randint(-1, 1) for x in range(min(count, 100))]
    if n < 2:  # it's a coin
        if count < 100:
            return [random.randint(0, 1) for x in range(count)]
        else:  # fake it
            return [int(random.normalvariate(.5 * count, (.75 * count) ** .5))]
    else:
        if count < 100:
            return [random.randint(1, n) for x in range(count)]
        else:  # fake it
            return [int(random.normalvariate(.5 * (1 + n) * count,
                                             (((n + 1) * (2 * n + 1) / 6. -
                                               (.5 * (1 + n)) ** 2) * count) ** .5))]


@api.command("roll")  # "dice")
def dice(text, sender=None, client=None):
    """<dice roll> - simulates dice rolls. Example: 'dice 2d20-d5+4 roll 2': D20s, subtract 1D5, add 4
    :type text: str
    """

    match = valid_diceroll.match(whitespace_re.sub("", text))
    if match:
        text, desc = match.groups()
    else:
        client.notice(sender.nick, "Invalid dice roll '{}'".format(text))
        return

    if "d" not in text:
        return

    spec = whitespace_re.sub('', text)
    if not valid_diceroll.match(spec):
        client.notice(sender.nick, "Invalid dice roll '{}'".format(text))
        return
    groups = sign_re.findall(spec)

    total = 0
    rolls = []

    for roll in groups:
        count, side = split_re.match(roll).groups()
        count = int(count) if count not in " +-" else 1
        if side.upper() == "F":  # fudge dice are basically 1d3-2
            for fudge in n_rolls(count, "F"):
                if fudge == 1:
                    rolls.append("\x033+\x0F")
                elif fudge == -1:
                    rolls.append("\x034-\x0F")
                else:
                    rolls.append("0")
                total += fudge
        elif side == "":
            total += count
        else:
            side = int(side)
            try:
                if count > 0:
                    d = n_rolls(count, side)
                    rolls += list(map(str, d))
                    total += sum(d)
                else:
                    d = n_rolls(-count, side)
                    rolls += [str(-x) for x in d]
                    total -= sum(d)
            except OverflowError:
                # I have never seen this happen. If you make this happen, you win a cookie
                return "Thanks for overflowing a float, jerk >:["

    if desc:
        return "{}: {} ({})".format(desc.strip(), total, ", ".join(rolls))
    else:
        return "{} ({})".format(total, ", ".join(rolls))
