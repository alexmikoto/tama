import asyncio as aio
import signal
import traceback
import logging
import logging.config
from types import FrameType

from tama.config import read_config
from tama.core import TamaBot


async def main():
    loop = aio.get_running_loop()

    cfg = read_config("config.toml")
    if cfg.logging:
        logging.config.dictConfig(cfg.logging)

    bot = TamaBot(cfg)
    await bot.setup_db()
    await bot.create_clients_from_config()

    # Graceful shutdown handlers
    def sigint():
        bot.shutdown("Keyboard interrupt")

    def sigterm():
        bot.shutdown("Received SIGTERM")

    # Orphaned exception handler
    def exception_handler(loop: aio.AbstractEventLoop, context: dict):
        exc = context["exception"]
        exc_info = type(exc), exc, exc.__traceback__
        logging.getLogger("tama.__main__").exception(
            "Caught orphaned exception", exc_info=exc_info
        )

    loop.add_signal_handler(signal.SIGINT, sigint)
    loop.add_signal_handler(signal.SIGTERM, sigterm)
    loop.set_exception_handler(exception_handler)

    while (status := await bot.run()) != TamaBot.ExitStatus.QUIT:
        if status == TamaBot.ExitStatus.RELOAD:
            await aio.sleep(5)  # Wait 5 seconds before reloading
            cfg = read_config("config.toml")
            bot = TamaBot(cfg)
            await bot.create_clients_from_config()


if __name__ == "__main__":
    aio.run(main())
