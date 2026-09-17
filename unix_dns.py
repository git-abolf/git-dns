"""Linux and macOS DNS control.

Windows had real system DNS switching (netsh); Linux/macOS only had DNS
*testing* through the Kivy fallback. This module gives them real switching
too, so "cross platform" is accurate for desktop, not just DNS benchmarking.

Linux: tries `nmcli` (NetworkManager) first, then `resolvectl` (systemd-resolved).
macOS: uses `networksetup`.
Neither requires a shell string, so adapter/service names can't be injected.
"""
import ipaddress
import platform
import shutil
import subprocess

from app.core.logger import get_logger

log = get_logger("unix_dns")


def _run(args, timeout=10):
    return subprocess.run(args, shell=False, capture_output=True, text=True, timeout=timeout)


def _validate_ips(*values):
    out = []
    for v in values:
        if v and v.strip():
            out.append(str(ipaddress.ip_address(v.strip())))
    return out


def _has(cmd):
    return shutil.which(cmd) is not None


# ---------------------------------------------------------------- Linux ----
def linux_list_connections():
    if not _has("nmcli"):
        return []
    try:
        out = _run(["nmcli", "-t", "-f", "NAME,DEVICE,STATE", "connection", "show", "--active"]).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("nmcli list failed: %s", exc)
        return []
    names = []
    for line in out.strip().splitlines():
        parts = line.split(":")
        if parts and parts[0]:
            names.append(parts[0])
    return names


def linux_apply_dns(connection: str, servers):
    servers = _validate_ips(*servers)
    if not servers:
        raise ValueError("No valid DNS servers supplied")
    if _has("nmcli"):
        _run(["nmcli", "connection", "modify", connection, "ipv4.dns", " ".join(servers)])
        _run(["nmcli", "connection", "modify", connection, "ipv4.ignore-auto-dns", "yes"])
        result = _run(["nmcli", "connection", "up", connection])
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "nmcli connection up failed")
        log.info("Applied DNS %s via nmcli on %s", servers, connection)
        return
    if _has("resolvectl"):
        result = _run(["resolvectl", "dns", connection, *servers])
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "resolvectl dns failed")
        log.info("Applied DNS %s via resolvectl on %s", servers, connection)
        return
    raise RuntimeError("Neither nmcli nor resolvectl is available on this system")


def linux_reset_dhcp(connection: str):
    if _has("nmcli"):
        _run(["nmcli", "connection", "modify", connection, "ipv4.ignore-auto-dns", "no"])
        _run(["nmcli", "connection", "modify", connection, "ipv4.dns", ""])
        _run(["nmcli", "connection", "up", connection])
        log.info("Reset %s to DHCP DNS via nmcli", connection)
        return
    if _has("resolvectl"):
        _run(["resolvectl", "revert", connection])
        log.info("Reverted %s via resolvectl", connection)
        return
    raise RuntimeError("Neither nmcli nor resolvectl is available on this system")


def linux_flush_cache():
    if _has("resolvectl"):
        result = _run(["resolvectl", "flush-caches"])
        if result.returncode == 0:
            log.info("Flushed DNS cache via resolvectl")
            return
    if _has("systemd-resolve"):
        _run(["systemd-resolve", "--flush-caches"])
        log.info("Flushed DNS cache via systemd-resolve")
        return
    raise RuntimeError("No known DNS cache flush mechanism found (resolvectl/systemd-resolve)")


# ---------------------------------------------------------------- macOS ----
def macos_list_services():
    if not _has("networksetup"):
        return []
    out = _run(["networksetup", "-listallnetworkservices"]).stdout
    lines = [l for l in out.splitlines() if l and not l.startswith("*") and "An asterisk" not in l]
    return lines


def macos_apply_dns(service: str, servers):
    servers = _validate_ips(*servers)
    if not servers:
        raise ValueError("No valid DNS servers supplied")
    result = _run(["networksetup", "-setdnsservers", service, *servers])
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "networksetup -setdnsservers failed")
    log.info("Applied DNS %s via networksetup on %s", servers, service)


def macos_reset_dhcp(service: str):
    result = _run(["networksetup", "-setdnsservers", service, "Empty"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "networksetup reset failed")
    log.info("Reset %s to DHCP DNS via networksetup", service)


def macos_flush_cache():
    _run(["dscacheutil", "-flushcache"])
    result = _run(["killall", "-HUP", "mDNSResponder"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "mDNSResponder restart failed")
    log.info("Flushed DNS cache via dscacheutil/mDNSResponder")


def is_supported():
    system = platform.system()
    if system == "Linux":
        return _has("nmcli") or _has("resolvectl")
    if system == "Darwin":
        return _has("networksetup")
    return False
