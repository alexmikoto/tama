import random

from tama import api

off_words = []
theo_wisdom = []


@api.on_load()
def load(bot: api.Bot = None):
    off_path = bot.data_path / "cunt.txt"
    theo_path = bot.data_path / "theo.txt"
    global off_words
    global theo_wisdom
    with open(off_path, encoding="utf-8") as f:
        off_words = [line.strip() for line in f.readlines() if not line.startswith("//")]
    with open(theo_path, encoding="utf-8") as f:
        theo_wisdom = [line.strip() for line in f.readlines() if not line.startswith("//")]


@api.command("cunt", "cunnt", auto_help=False)
async def cunt(text: str):
    """- hands out a OFFENSIVE word m8"""
    return random.choice(off_words)


@api.command(auto_help=False)
async def cunny(text: str, client: api.Client = None, sender: api.User = None):
    """- STOP """
    client.action(f"arrests {sender.nick}")


@api.command(auto_help=False)
async def theo(text: str):
    """- hands out theo's wisdom"""
    return random.choice(theo_wisdom)
