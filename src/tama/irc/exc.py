__all__ = ["ParseError", "InvalidIRCCommandError", "InvalidCTCPCommandError"]


class ParseError(Exception):
    """
    Represents any error encountered while parsing an IRC message.
    """
    origin: bytes

    def __init__(self, origin: bytes) -> None:
        self.origin = origin

    def __str__(self) -> str:
        return "Parse Error"


class InvalidIRCCommandError(ParseError):
    """
    Received a valid message, but the command given is not valid IRC.
    """

    command: str

    def __init__(self, origin: bytes, command: str) -> None:
        super().__init__(origin)
        self.command = command

    def __str__(self) -> str:
        return f"Parse Error: IRC command '{self.command}' is not valid"


class InvalidCTCPCommandError(ParseError):
    """
    Received a valid message, but the command given is not valid CTCP.
    """

    command: str

    def __init__(self, origin: bytes, command: str) -> None:
        super().__init__(origin)
        self.command = command

    def __str__(self) -> str:
        return f"Parse Error: CTCP command '{self.command}' is not valid"
