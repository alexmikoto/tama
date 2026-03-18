from dataclasses import dataclass

from tama.irc.command import *
from tama.irc.ctcp import *
from tama.irc.user import *
from tama.irc.exc import *

__all__ = ["IRCMessage"]

UNKNOWN_USER = IRCUser(nick="<unknown>", user="<unknown>", host="<unknown>")


@dataclass
class IRCMessage:
    command: str
    prefix: str | None = None
    middle: tuple[str, ...] = ()
    trailing: str | None = None

    # Keep the original numeric for raw access
    numeric: str | None = None

    # UTF-8 assumed unless specified otherwise
    encoding: str = "utf-8"

    # CTCP specific stuff
    @dataclass
    class CTCP:
        command: str
        text: str | None = None

    # CTCP specific stuff
    ctcp: IRCMessage.CTCP | None = None

    @classmethod
    def parse(cls, msg: bytes, encoding: str = "utf-8") -> "IRCMessage":
        # Deal with prefixed messages
        prefix = None
        if msg[0] == 0x3a:  # ':'
            sep = msg.find(b" ")
            prefix, msg = (
                msg[1: sep].decode(encoding), msg[sep+1:]
            )

        if (sep := msg.find(b" ")) == -1:
            # We can only get here with either a message of the form
            # MESSAGE\r\n or with garbage
            sep = len(msg)
        command, msg = msg[: sep].decode(encoding), msg[sep+1:]

        if (sep := msg.find(b":")) == -1:
            # No trailing, but we may have a middle
            middle_b, trailing_b = msg, None
        else:
            middle_b, trailing_b = msg[: sep], msg[sep+1:]

        if len(middle_b) > 0:
            middle = tuple(
                m.decode(encoding)
                for m in middle_b.split(b" ") if len(m) > 0
            )
        else:
            middle = tuple()

        if trailing_b:
            trailing = trailing_b.decode(encoding)
        else:
            trailing = None

        if len(command) == 3 and "0" <= command[0] <= "9":
            # Handle numeric replies
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
            command == "PRIVMSG"
            and trailing.startswith("\x01")
            and trailing.endswith("\x01")
        ):
            ctcp_payload: str = trailing[1:-1]
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
            # Make sure we don't keep redundant information to not break
            # serialization
            trailing = None

        return cls(
            encoding=encoding,
            prefix=prefix,
            command=command,
            numeric=numeric,
            middle=middle,
            trailing=trailing,
            ctcp=ctcp,
        )

    @property
    def raw(self) -> bytes:
        buf = bytearray()

        if self.prefix:
            buf.extend(f":{self.prefix} ".encode(self.encoding))

        if not self.numeric:
            buf.extend(self.command.encode(self.encoding))
        else:
            buf.extend(self.numeric.encode(self.encoding))

        if len(self.middle) > 0:
            for mid in self.middle:
                buf.extend(f" {mid}".encode(self.encoding))

        if self.trailing:
            buf.extend(f" :{self.trailing}".encode(self.encoding))

        if self.ctcp:
            buf.extend(" :".encode(self.encoding))
            buf.extend(b"\x01")
            buf.extend(self.ctcp.command.encode(self.encoding))
            if self.ctcp.text:
                buf.extend(f" {self.ctcp.text}".encode(self.encoding))
            buf.extend(b"\x01")

        buf.extend(b"\r\n")
        return bytes(buf)

    def parse_prefix_as_user(self) -> IRCUser:
        try:
            return IRCUser.from_address(self.prefix)
        except (AttributeError, ValueError):
            return UNKNOWN_USER
