"""
CTCP commands according to draft-oakley-irc-ctcp-02 and/or common practices.

See: https://tools.ietf.org/html/draft-oakley-irc-ctcp-02
"""

__all__ = ["CTCP_COMMANDS"]

CTCP_COMMANDS = {
    "ACTION",      # ACTION <text>
    "CLIENTINFO",  # CLIENTINFO
    "DCC",         # DCC <type> <argument> <host> <port>
    "FINGER",      # [Obsolete] FINGER
    "PING",        # PING <info>
    "SOURCE",      # [Obsolete] SOURCE
    "TIME",        # TIME
    "VERSION",     # VERSION
    "USERINFO",    # [Obsolete] USERINFO
}
