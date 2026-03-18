__all__ = ["InvalidIRCCommandError", "InvalidCTCPCommandError"]


class InvalidIRCCommandError(Exception):
    """
    Received a valid message, but the command given is not valid IRC.
    """

    command: str

    def __init__(self, command: str) -> None:
        self.command = command


class InvalidCTCPCommandError(Exception):
    """
    Received a valid message, but the command given is not valid CTCP.
    """

    command: str

    def __init__(self, command: str) -> None:
        self.command = command
