import re
import time

from sqlalchemy import (
    Column,
    Float,
    PrimaryKeyConstraint,
    String,
    Table,
    and_,
    select,
)

from tama import api
from tama.irc.event import MessagedEvent, ActionEvent
from tama.util.irc import is_valid_nick
from tama.util.legacy import timeformat

table = Table(
    "seen_user",
    api.DB.metadata,
    Column("name", String),
    Column("time", Float),
    Column("quote", String),
    Column("chan", String),
    Column("host", String),
    PrimaryKeyConstraint("name", "chan"),
)


async def track_seen(evt: MessagedEvent | ActionEvent, db: api.DB.Conn) -> None:
    """Tracks messages for the .seen command"""
    # keep private messages private
    now = time.time()
    if evt.where[:1] == "#" and not re.findall(
        "^s/.*/.*/$", evt.message.lower()
    ):
        nick = evt.who.nick.lower()
        msg = evt.message
        if isinstance(evt, ActionEvent):
            msg = f"\x01ACTION {msg}\x01"

        res = await db.execute(
            table.update()
            .where(
                and_(
                    table.c.name == nick,
                    table.c.chan == evt.where,
                )
            )
            .values(time=now, quote=msg, host=evt.who.address)
        )
        if res.rowcount == 0:
            await db.execute(
                table.insert().values(
                    name=nick,
                    time=now,
                    quote=msg,
                    chan=evt.where,
                    host=evt.who.address,
                )
            )

        await db.commit()


@api.event([MessagedEvent, ActionEvent])
async def chat_tracker(evt: MessagedEvent | ActionEvent, db: api.DB.Conn) -> None:
    await track_seen(evt, db)


@api.command()
async def seen(text: str, channel: str, sender: api.User, client: api.Client, db: api.DB.Conn) -> str:
    """<nick> <channel> - tells when a nickname was last in active in one of my channels"""

    if client.nickname.lower() == text.lower():
        return "You need to get your eyes checked."

    if text.lower() == sender.nick.lower():
        return "Have you looked in a mirror lately?"

    if not is_valid_nick(text):
        return "I can't look up that name, its impossible to use!"

    rs = await db.execute(
        select(table.c.name, table.c.time, table.c.quote).where(
            and_(table.c.name == text.lower(), table.c.chan == channel)
        )
    )
    last_seen = rs.fetchone()

    if not last_seen:
        return f"I've never seen {text} talking in this channel."

    when = last_seen[1]
    if isinstance(when, str):
        when = float(when.strip())

    reltime = timeformat.time_since(when)
    msg = last_seen[2]
    if msg.startswith("\1ACTION"):
        stripped = msg.strip("\1 ")[6:].strip()
        return f"{text} was last seen {reltime} ago: * {text} {stripped}"

    return f"{text} was last seen {reltime} ago saying: {msg}"
