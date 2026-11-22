"""Python socket audit guard, inherited by validation's Python subprocesses."""
import ipaddress
import os
import socket
import sys


def local(host):
    if host is None or host == "localhost" or host == b"localhost":
        return True
    try:
        address = ipaddress.ip_address(host.decode() if isinstance(host, bytes) else host)
        return address.is_loopback or bool(getattr(address, "ipv4_mapped", None)
                                           and address.ipv4_mapped.is_loopback)
    except (ValueError, TypeError):
        return False


def network_guard(event, args):
    if event in {"socket.connect", "socket.bind", "socket.sendto", "socket.sendmsg"}:
        sock, address = args
        denied = sock.family not in (socket.AF_INET, socket.AF_INET6, socket.AF_UNIX) or (
            sock.family in (socket.AF_INET, socket.AF_INET6) and address is not None
            and not (isinstance(address, tuple) and local(address[0])))
    elif event in {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr", "socket.getnameinfo"}:
        host = args[0]
        denied = not local(host[0] if isinstance(host, tuple) else host)
    else:
        return
    if denied:
        if not os.environ.get("DC03C_GUARD_PROBE"):
            with open(os.environ["DC03C_GUARD_LOG"], "ab") as record:
                record.write(b"blocked Python socket operation\n")
        raise PermissionError("external Python networking blocked by DC03C")


sys.addaudithook(network_guard)
os.environ["DC03C_GUARD_ACTIVE"] = "1"
