from __future__ import annotations

import random

from tama import api
from tama.util.legacy import colors

responses: list[str] = []


@api.on_load()
def load_responses(bot: api.Bot) -> None:
    path = bot.data_path / "8ball_responses.txt"
    responses.clear()
    with open(path, encoding="utf-8") as f:
        responses.extend(
            line.strip() for line in f.readlines() if not line.startswith("//")
        )


@api.command("8ball", "8", "eightball")
async def eightball(text, client: api.Client) -> None:
    """<question> - asks the all knowing magic electronic eight ball <question>"""
    magic = random.choice(responses)
    message = colors.parse(f"shakes the magic 8 ball... {magic}")

    client.action(message)
