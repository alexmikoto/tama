from dataclasses import dataclass
from typing import Optional, List, Dict

__all__ = ["Config", "ServerConfig", "TamaConfig"]


@dataclass
class ServerServiceAuthConfig:
    service: Optional[str]
    command: Optional[str]
    username: Optional[str]
    password: str


@dataclass
class ServerConfig:
    host: str
    port: str
    nick: str
    user: str
    realname: str
    channels: Optional[List[str]]
    service_auth: Optional[ServerServiceAuthConfig]


@dataclass
class TamaConfig:
    prefix: str
    log_folder: Optional[str]
    log_raw: Optional[bool]
    log_irc: Optional[bool]


@dataclass
class Config:
    server: Dict[str, ServerConfig]
    tama: TamaConfig
    logging: Optional[dict]
