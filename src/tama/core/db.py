import logging
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncConnection,
    AsyncTransaction,
)


class TamaDB:
    metadata = MetaData()
    Conn = AsyncConnection
    Tx = AsyncTransaction

    engine: AsyncEngine

    def __init__(self, engine):
        self.engine = engine

    @classmethod
    def create(cls, config: dict):
        logging.getLogger(__name__).info(
            "Connecting to database: %s",
            ", ".join(f"{k}=\"{v}\"" for k, v in config.items())
        )
        engine = create_async_engine(**config)
        return cls(engine)

    async def create_all(self):
        logging.getLogger(__name__).info("Creating all tables in schema")
        async with self.engine.begin() as conn:
            await conn.run_sync(self.metadata.create_all)

    async def connect(self) -> AsyncConnection:
        # Don't run this in a context manager as we'll handle this in the
        # plugin API
        return await self.engine.connect()
