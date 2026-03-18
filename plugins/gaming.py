"""
gaming.py

Dice, coins, and random generation for gaming.

This plugin has been ported directly from CloudBot, which is under the GPLv3
license.

All credit goes to the Cloudbot maintainers.

Modified By:
    - Luke Rogers <https://github.com/lukeroge>

License:
    GPL v3
"""

import random
import re

from tama import api

whitespace_re = re.compile(r"\s+")
valid_diceroll = re.compile(
    r"^([+-]?(?:\d+|\d*d(?:\d+|F))(?:[+-](?:\d+|\d*d(?:\d+|F)))*)( .+)?$", re.I
)
sign_re = re.compile(r"[+-]?(?:\d*d)?(?:\d+|F)", re.I)
split_re = re.compile(r"([\d+-]*)d?(F|\d*)", re.I)


def clamp(n, min_value, max_value):
    """Restricts a number to a certain range of values,
    returning the min or max value if the value is too small or large, respectively
    :param n: The value to clamp
    :param min_value: The minimum possible value
    :param max_value: The maximum possible value
    :return: The clamped value
    """
    return min(max(n, min_value), max_value)


def n_rolls(count, n):
    """roll an n-sided die count times"""
    if n in ("f", "F"):
        return [random.randint(-1, 1) for _ in range(min(count, 100))]

    if count < 100:
        return [random.randint(1, n) for _ in range(count)]

    normalvariate = approximate(count, n)

    return [int(normalvariate)]


def approximate(count, n):
    # Calculate a random sum approximated using a randomized normal variate with the midpoint used as the mu
    # and an approximated standard deviation based on variance as the sigma
    mid = 0.5 * (n + 1) * count
    var = (n**2 - 1) / 12
    adj_var = (var * count) ** 0.5
    normalvariate = random.normalvariate(mid, adj_var)
    return normalvariate


@api.command("roll", "dice")
def dice(text, client: api.Client = None):
    """<dice roll> - simulates dice rolls. Example: 'dice 2d20-d5+4 roll 2': D20s, subtract 1D5, add 4"""
    match = valid_diceroll.match(text)
    if not match:
        client.notice(f"Invalid dice roll '{text}'")
        return None

    text, desc = match.groups()

    if "d" not in text:
        return None

    spec = whitespace_re.sub("", text)
    groups = sign_re.findall(spec)

    total = 0
    rolls = []

    for roll in groups:
        match = split_re.match(roll)
        if match is None:
            return f"Can't match roll: {roll}"

        _count, _side = match.groups()
        count = int(_count) if _count not in " +-" else 1
        if _side.upper() == "F":  # fudge dice are basically 1d3-2
            for fudge in n_rolls(count, "F"):
                if fudge == 1:
                    rolls.append("\x033+\x0f")
                elif fudge == -1:
                    rolls.append("\x034-\x0f")
                else:
                    rolls.append("0")
                total += fudge
        elif _side == "":
            total += count
        else:
            side = int(_side)
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
                client.message("Thanks for overflowing a float, jerk >:[")
                raise

    if desc:
        return f"{desc.strip()}: {total} ({', '.join(rolls)})"

    return f"{total} ({', '.join(rolls)})"


@api.command()
def choose(text, client: api.Client = None):
    """<choice1>, [choice2], [choice3], etc. - randomly picks one of the given choices"""
    choices = re.findall(r"([^,]+)", text.strip())
    if len(choices) == 1:
        choices = choices[0].split(" or ")
        if len(choices) == 1:
            client.message("Nothing to choose.")
            return None

    return random.choice([choice.strip() for choice in choices])


@api.command(auto_help=False)
def coin(text, client: api.Client = None):
    """[amount] - flips [amount] coins"""

    if text:
        try:
            amount = int(text)
        except (ValueError, TypeError):
            client.notice(f"Invalid input '{text}': not a number")
            return None
    else:
        amount = 1

    if amount == 1:
        client.action(f"flips a coin and gets {random.choice(['heads', 'tails'])}.")
        return None

    if amount == 0:
        client.action("makes a coin flipping motion")
        return None

    mu = 0.5 * amount
    sigma = (0.75 * amount) ** 0.5
    n = random.normalvariate(mu, sigma)
    heads = clamp(round(n), 0, amount)
    tails = amount - heads
    client.action(f"flips {amount} coins and gets {heads} heads and {tails} tails.")
    return None
