import fnmatch

from tama.config.schema import PermissionGroupConfig
from tama.irc.user import IRCUser

__all__ = ["ACL"]


class ACL:
    __slots__ = ("_acl",)

    _acl: dict

    def __init__(self, acl_config: dict[str, PermissionGroupConfig]) -> None:
        self._acl = {}
        for group in acl_config.keys():
            for addr in acl_config[group].users:
                if addr in self._acl:
                    self._acl[addr].extend(
                        acl_config[group].perms
                    )
                else:
                    self._acl[addr] = acl_config[group].perms

    def check_permission(self, user: IRCUser, permission: str) -> bool:
        perms = self._acl.get(user.address, [])
        if not perms:
            for addr in self._acl.keys():
                if fnmatch.fnmatch(user.address, addr):
                    perms = self._acl[addr]
                    break
        return permission in perms
