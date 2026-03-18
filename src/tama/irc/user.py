from dataclasses import dataclass

__all__ = ["IRCUser"]


@dataclass
class IRCUser:
    nick: str
    user: str
    host: str

    @property
    def address(self) -> str:
        return f"{self.nick}!{self.user}@{self.host}"

    @classmethod
    def from_address(cls, address: str) -> "IRCUser":
        nick, prefix = address.split("!", 1)
        user, host = prefix.split("@", 1)
        return IRCUser(
            nick=nick,
            user=user,
            host=host,
        )
