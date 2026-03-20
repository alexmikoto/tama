"""
Handles the parsing of IRC messages from a byte stream.

The pseudo BNF representation of IRC message format according to RFC1459 is:

<message>  ::= [':' <prefix> <SPACE> ] <command> <params> <crlf>
<prefix>   ::= <servername> | <nick> [ '!' <user> ] [ '@' <host> ]
<command>  ::= <letter> { <letter> } | <number> <number> <number>
<SPACE>    ::= ' ' { ' ' }
<params>   ::= <SPACE> [ ':' <trailing> | <middle> <params> ]

<middle>   ::= <Any *non-empty* sequence of octets not including SPACE
               or NUL or CR or LF, the first of which may not be ':'>
<trailing> ::= <Any, possibly *empty*, sequence of octets not including
                 NUL or CR or LF>

<crlf>     ::= CR LF

See also: https://tools.ietf.org/html/rfc1459
          https://tools.ietf.org/html/rfc2812

"""
import asyncio as aio
import ssl
from logging import getLogger

from tama.irc.exc import ParseError
from tama.irc.stream.payloads import IRCMessage

__all__ = ["IRCStream", "IRCMessage"]


class IRCStream:
    encoding = "utf-8"

    reader: aio.StreamReader
    writer: aio.StreamWriter

    def __init__(
        self,
        reader: aio.StreamReader,
        writer: aio.StreamWriter,
    ) -> None:
        super().__init__()
        self.reader = reader
        self.writer = writer
        self.buffer = bytearray()

    @classmethod
    async def create(cls, host: str, port: int, secure: bool = False):
        if not secure:
            getLogger(__name__).info(f"Connecting to irc://{host}:{port}")
        else:
            getLogger(__name__).info(f"Connecting to ircs://{host}:{port}")
        ssl_ctx = None
        if secure:
            ssl_ctx = ssl.create_default_context()
        reader, writer = await aio.open_connection(host, port, ssl=ssl_ctx)
        return cls(reader, writer)

    async def read_messages(self) -> tuple[list[IRCMessage], list[ParseError]] | None:
        """
        Reads a batch of IRC messages from the inbound TCP stream. A list of
        parsed messages will be returned, unless the connection is closed and
        has reached EOF. In the latter case, None will be returned.

        :return: List of IRC messages or None.
        """
        messages = []
        errors = []
        data = await self.reader.read(1024)

        if len(data) == 0:
            # Connection closed
            return None

        if (lim := data.find(b"\r\n")) == -1:
            # If there is no delimiter assume the message is incomplete
            self.buffer.extend(data)
            return messages, errors

        # Get buffered message
        if len(self.buffer) > 0:
            msg, data = self.buffer + data[: lim], data[lim + 2:]
            try:
                messages.append(IRCMessage.parse(msg, encoding=self.encoding))
            except ParseError as e:
                errors.append(e)
            self.buffer.clear()

        # Get all other messages
        while (lim := data.find(b"\r\n")) != -1:
            msg, data = data[: lim], data[lim + 2:]
            try:
                messages.append(IRCMessage.parse(msg, encoding=self.encoding))
            except ParseError as e:
                errors.append(e)

        # Buffer remaining data for next read
        if len(data) > 0:
            self.buffer = bytearray(data)

        return messages, errors

    async def send_message(self, msg: IRCMessage) -> None:
        self.writer.write(msg.raw)
        await self.writer.drain()
