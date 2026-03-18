import tomllib

from .schema_validate import validate_map_schema
from .schema import Config

__all__ = ["read_config"]


def read_config(filename: str) -> Config:
    with open(filename, "r") as config:
        cfg = tomllib.loads(config.read())
        return validate_map_schema(cfg, Config)
