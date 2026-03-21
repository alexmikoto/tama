"""
factoids.py

This plugin has been ported directly from CloudBot, which is under the GPLv3
license.

All credit goes to the Cloudbot maintainers.
"""
import re
import string
from collections import defaultdict

from sqlalchemy import Column, PrimaryKeyConstraint, String, Table, and_

from tama import api
from tama.util.legacy import colors, web
from tama.util.legacy.formatting import gen_markdown_table, get_text_list
from tama.util.legacy.web import NoPasteException

# below is the default factoid in every channel you can modify it however you like
default_dict = {"commands": "https://snoonet.org/gonzobot"}
factoid_cache: dict[str, dict[str, str]] = defaultdict(default_dict.copy)

FACTOID_CHAR = "?"  # TODO: config

table = Table(
    "factoids",
    api.DB.metadata,
    Column("word", String),
    Column("data", String),
    Column("nick", String),
    Column("chan", String),
    PrimaryKeyConstraint("word", "chan"),
)


@api.on_connect()
async def load_cache(db: api.DB.Conn) -> None:
    new_cache = factoid_cache.copy()
    new_cache.clear()
    for row in await db.execute(table.select()):
        # assign variables
        chan = row.chan
        word = row.word
        data = row.data
        new_cache[chan][word] = data

    factoid_cache.clear()
    factoid_cache.update(new_cache)


async def add_factoid(db: api.DB.Conn, word: str, chan: str, data: str, nick: str) -> None:
    if word in factoid_cache[chan]:
        # if we have a set value, update
        await db.execute(
            table.update()
            .values(data=data, nick=nick, chan=chan)
            .where(table.c.chan == chan)
            .where(table.c.word == word)
        )
        await db.commit()
    else:
        # otherwise, insert
        await db.execute(
            table.insert().values(word=word, data=data, nick=nick, chan=chan)
        )
        await db.commit()
    await load_cache(db)


async def del_factoid(db: api.DB.Conn, chan: str, word: list[str] = None) -> None:
    clause = table.c.chan == chan

    if word is not None:
        clause = and_(clause, table.c.word.in_(word))

    await db.execute(table.delete().where(clause))
    await db.commit()
    await load_cache(db)


@api.command("r", "remember", permissions=["op", "chanop"])
async def remember(text: str, sender: api.User, db: api.DB.Conn, channel: str, notice: api.Func) -> None:
    """<word> [+]<data> - remembers <data> with <word> - add + to <data> to append. If the input starts with <act> the
    message will be sent as an action. If <user> is in the message it will be replaced by input arguments when command
    is called."""
    try:
        word, data = text.split(None, 1)
    except ValueError:
        notice("Invalid format")
        return

    word = word.lower()
    try:
        old_data = factoid_cache[channel][word]
    except LookupError:
        old_data = None

    if data.startswith("+") and old_data:
        # remove + symbol
        new_data = data[1:]
        # append new_data to the old_data
        puncts = f"{string.punctuation} "
        if len(new_data) > 1 and new_data[1] in puncts:
            data = old_data + new_data
        else:
            data = f"{old_data} {new_data}"
        notice(f"Appending \x02{new_data}\x02 to \x02{old_data}\x02")
    else:
        notice(
            f"Remembering \x02{data}\x02 for \x02{word}\x02. Type {FACTOID_CHAR}{word} to see it."
        )
        if old_data:
            notice(f"Previous data was \x02{old_data}\x02")

    await add_factoid(db, word, channel, data, sender.nick)


async def paste_facts(facts, raise_on_no_paste=False):
    headers = ("Command", "Output")
    data = [(FACTOID_CHAR + fact[0], fact[1]) for fact in sorted(facts.items())]
    tbl = gen_markdown_table(headers, data).encode("UTF-8")
    return api.run_sync_function(
        web.paste, tbl, "md", "hastebin", raise_on_no_paste=raise_on_no_paste
    )


async def remove_fact(chan, names, db, notice) -> None:
    found: dict[str, str] = {}
    missing = []
    for name in names:
        data = factoid_cache[chan].get(name.lower())
        if data:
            found[name] = data
        else:
            missing.append(name)

    if missing:
        notice(
            f"Unknown factoids: {get_text_list([repr(s) for s in missing], 'and')}"
        )

    if found:
        try:
            notice(f"Removed Data: {paste_facts(found, True)}")
        except NoPasteException:
            notice("Unable to paste removed data, not removing facts")
            return

        await del_factoid(db, chan, list(found.keys()))


@api.command("f", "forget", permissions=["op", "chanop"])
async def forget(text: str, channel: str, db: api.DB.Conn, notice: api.Func) -> None:
    """<word>... - Remove factoids with the specified names"""
    await remove_fact(channel, text.split(), db, notice)


@api.command(
    "forgetall", "clearfacts", auto_help=False, permissions=["op", "chanop"]
)
async def forget_all(channel: str, db: api.DB.Conn) -> str:
    """- Remove all factoids in the current channel"""
    await del_factoid(db, channel)
    return "Facts cleared."


@api.command()
def info(text: str, channel: str, notice: api.Func) -> None:
    """<factoid> - shows the source of a factoid"""

    text = text.strip().lower()

    if text in factoid_cache[channel]:
        notice(factoid_cache[channel][text])
    else:
        notice("Unknown Factoid.")


factoid_re = re.compile(rf"^{re.escape(FACTOID_CHAR)} ?(.+)", re.I)


@api.regex(factoid_re)
def factoid(origin: str, match: re.Match, channel: str, reply: api.Func, action: api.Func) -> None:
    """<word> - shows what data is associated with <word>"""
    arg1 = ""
    if len(origin.split()) >= 2:
        arg1 = origin.split()[1]
    # split up the input
    split = match.group(1).strip().split(" ")
    factoid_id = split[0].lower()

    if factoid_id in factoid_cache[channel]:
        data = factoid_cache[channel][factoid_id]
        result = data

        # factoid post-processors
        result = colors.parse(result)
        if arg1:
            result = result.replace("<user>", arg1)
        if result.startswith("<act>"):
            result = result[5:].strip()
            action(result)
        else:
            reply(result)


@api.command("listfacts", auto_help=False)
async def listfactoids(notice: api.Func, channel: str) -> None:
    """- lists all available factoids"""
    reply_text: list[str] = []
    reply_text_length = 0
    for word in sorted(factoid_cache[channel].keys()):
        text = FACTOID_CHAR + word
        added_length = len(text) + 2
        if reply_text_length + added_length > 400:
            notice(", ".join(reply_text))
            # Take a chill pill before getting murdered for flooding
            await api.sleep(0.5)
            reply_text = []
            reply_text_length = 0

        reply_text.append(text)
        reply_text_length += added_length

    notice(", ".join(reply_text))


@api.command("listdetailedfacts", auto_help=False)
async def listdetailedfactoids(channel: str):
    """- lists all available factoids with their respective data"""
    return await paste_facts(factoid_cache[channel])
