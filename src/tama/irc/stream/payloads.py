from dataclasses import dataclass

from tama.irc.command import *
from tama.irc.ctcp import *
from tama.irc.user import *
from tama.irc.exc import *

__all__ = ["IRCMessage"]

UNKNOWN_USER = IRCUser(
    nick="<unknown>", user="<unknown>", host="<unknown>", is_nil=True
)

do_not_parse_numerics = (
    "RPL_MYINFO",
    "RPL_ISUPPORT",
    "RPL_LUSEROP",
    "RPL_LUSERUNKNOWN",
    "RPL_LUSERCHANNELS",
)


@dataclass
class IRCMessage:
    command: str
    tags: str | None = None
    prefix: str | None = None
    params: tuple[str, ...] = ()

    # Keep the original numeric for raw access
    numeric: str | None = None

    # Keep the original message for debugging
    origin: bytes = None

    # UTF-8 assumed unless specified otherwise
    encoding: str = "utf-8"

    # CTCP specific stuff
    @dataclass
    class CTCP:
        command: str
        text: str | None = None

        @property
        def frame(self):
            res = f"\x01{self.command}"
            if self.text is not None:
                res += f" {self.text}"
            res += "\x01"
            return res

    # CTCP specific stuff
    ctcp: IRCMessage.CTCP | None = None

    @classmethod
    def parse(cls, msg: bytes, encoding: str = "utf-8") -> "IRCMessage":
        remaining = msg

        # Deal with tags
        tags = None
        if msg[0] == 0x40:  # '@'
            sep = remaining.find(b" ")
            tags, remaining = (
                remaining[1: sep].decode(encoding), remaining[sep+1:]
            )

        # Deal with prefixed messages
        prefix = None
        if msg[0] == 0x3a:  # ':'
            sep = remaining.find(b" ")
            prefix, remaining = (
                remaining[1: sep].decode(encoding), remaining[sep+1:]
            )

        # Get command
        if (sep := remaining.find(b" ")) == -1:
            # We can only get here with either a message of the form
            # MESSAGE\r\n or with garbage
            sep = len(remaining)
        command, remaining = remaining[: sep].decode(encoding), remaining[sep+1:]

        # Parse parameter list
        params: list[str] = []
        while len(remaining) > 0:
            # A semicolon lead indicates the rest of the message is a single
            # parameter
            if remaining[0] == 0x3a:  # ':'
                params.append(remaining[1:].decode(encoding))
                remaining = b""
            else:
                if (sep := remaining.find(b" ")) != -1:
                    param, remaining = remaining[: sep].decode(encoding), remaining[sep+1:]
                    params.append(param)
                else:
                    params.append(remaining.decode(encoding))
                    remaining = b""

        # Handle numeric replies
        if len(command) == 3 and "0" <= command[0] <= "9":
            numeric = command
            command = REPLY_CODES.get(command, None)
            if command is None:
                # Unknown reply code
                raise InvalidIRCCommandError(numeric)
        else:
            numeric = None
            if command not in COMMANDS:
                # Bad command
                raise InvalidIRCCommandError(command)

        # Check for CTCP encapsulation and parse messages
        ctcp = None
        if (
            (command == "PRIVMSG" or command == "NOTICE")
            and params[-1].startswith("\x01")
            and params[-1].endswith("\x01")
        ):
            ctcp_payload: str = params[-1][1:-1]
            ctcp_cmd, *ctcp_trailing = ctcp_payload.split(" ", 1)

            if ctcp_cmd not in CTCP_COMMANDS:
                raise InvalidCTCPCommandError(ctcp_cmd)

            # No need to parse CTCP message further as the only query with a
            # parameter list is DCC which is not supported.
            if len(ctcp_trailing) == 0:
                ctcp_trailing = None
            else:
                ctcp_trailing = ctcp_trailing[0]

            ctcp = cls.CTCP(
                command=ctcp_cmd,
                text=ctcp_trailing
            )

        return cls(
            origin=msg,
            encoding=encoding,
            tags=tags,
            prefix=prefix,
            command=command,
            numeric=numeric,
            params=tuple(params),
            ctcp=ctcp,
        )

    @classmethod
    def encapsulate_ctcp(
        cls,
        command: str,
        target: str,
        ctcp_command: str,
        ctcp_text: str,
        encoding: str = "utf-8",
    ) -> "IRCMessage":
        ctcp = cls.CTCP(
            command=ctcp_command,
            text=ctcp_text,
        )
        return cls(
            encoding=encoding,
            command=command,
            params=(target, ctcp.frame),
            ctcp=ctcp,
        )

    @property
    def raw(self) -> bytes:
        buf = bytearray()

        if self.tags:
            buf.extend(f"@{self.tags} ".encode(self.encoding))

        if self.prefix:
            buf.extend(f":{self.prefix} ".encode(self.encoding))

        if not self.numeric:
            buf.extend(self.command.encode(self.encoding))
        else:
            buf.extend(self.numeric.encode(self.encoding))

        if len(self.params[:-1]) > 0:
            for param in self.params[:-1]:
                buf.extend(f" {param}".encode(self.encoding))

        # CTCP serialization is a special case
        if not self.ctcp:
            if self.trailing.find(" ") != -1:
                buf.extend(f" :{self.trailing}".encode(self.encoding))
            else:
                buf.extend(f" {self.trailing}".encode(self.encoding))

        if self.ctcp:
            buf.extend(" :".encode(self.encoding))
            buf.extend(b"\x01")
            buf.extend(self.ctcp.command.encode(self.encoding))
            if self.ctcp.text:
                buf.extend(f" {self.ctcp.text}".encode(self.encoding))
            buf.extend(b"\x01")

        buf.extend(b"\r\n")
        return bytes(buf)

    @property
    def trailing(self) -> str | None:
        if len(self.params) > 0:
            return self.params[-1]
        else:
            return None

    def parse_prefix_as_user(self) -> IRCUser:
        try:
            return IRCUser.from_address(self.prefix)
        except (AttributeError, ValueError):
            return UNKNOWN_USER
