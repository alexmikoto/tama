from dataclasses import dataclass

__all__ = ["Config", "ServerConfig", "PermissionGroupConfig", "TamaConfig"]


@dataclass
class ServerServiceAuthConfig:
    service: str | None
    command: str | None
    username: str | None
    password: str


@dataclass
class ServerConfig:
    host: str
    port: str
    nick: str
    user: str
    realname: str
    channels: list[str] | None
    service_auth: ServerServiceAuthConfig | None


@dataclass
class PermissionGroupConfig:
    perms: list[str]
    users: list[str]


@dataclass
class TamaConfig:
    prefix: str
    log_folder: str | None
    log_raw: bool | None
    log_irc: bool | None
    plugin_folder: str | None
    data_folder: str | None
    db: dict | None
    permissions: dict[str, PermissionGroupConfig] | None
    plugins: dict[str, dict] | None


@dataclass
class Config:
    server: dict[str, ServerConfig]
    tama: TamaConfig
    logging: dict | None
