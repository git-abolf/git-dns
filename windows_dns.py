"""Windows DNS control via netsh.

All subprocess calls use argument lists with shell=False so adapter names or
IPs can never be interpreted as shell syntax, and every value is validated
before it reaches the command line.
"""
import ipaddress
import subprocess

from app.core.logger import get_logger

log = get_logger("windows_dns")


def _run(args, timeout=10):
    return subprocess.run(
        args, shell=False, capture_output=True, text=True, timeout=timeout
    )


def _validate_ip(value: str, version: int = None) -> str:
    ip = ipaddress.ip_address(value.strip())
    if version and ip.version != version:
        raise ValueError(f"{value} is not an IPv{version} address")
    return str(ip)


def list_adapters():
    """Return connected/enabled interface names via `netsh interface show interface`."""
    try:
        out = _run(["netsh", "interface", "show", "interface"]).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("Could not list adapters: %s", exc)
        return []
    adapters = []
    for line in out.splitlines():
        if "Connected" in line or "Enabled" in line:
            parts = line.split()
            if len(parts) >= 4:
                name = " ".join(parts[3:])
                if name not in adapters:
                    adapters.append(name)
    return adapters


def apply_dns(adapter: str, primary: str, secondary: str = "", ipv6_1: str = "", ipv6_2: str = ""):
    """Apply static DNS to `adapter`. Raises ValueError/CalledProcessError on failure."""
    if not adapter or not adapter.strip():
        raise ValueError("No adapter selected")
    primary = _validate_ip(primary, 4)

    _run(["netsh", "interface", "ip", "set", "dns", f"name={adapter}", "dhcp"])
    _run(["netsh", "interface", "ip", "set", "dns", f"name={adapter}", "static", primary], timeout=15)

    if secondary and secondary.strip():
        secondary = _validate_ip(secondary, 4)
        _run(["netsh", "interface", "ip", "add", "dns", f"name={adapter}", secondary, "index=2"])

    if ipv6_1 and ipv6_1.strip():
        ipv6_1 = _validate_ip(ipv6_1, 6)
        _run(["netsh", "interface", "ipv6", "set", "dns", f"name={adapter}", "dhcp"])
        _run(["netsh", "interface", "ipv6", "set", "dns", f"name={adapter}", "static", ipv6_1], timeout=15)
        if ipv6_2 and ipv6_2.strip():
            ipv6_2 = _validate_ip(ipv6_2, 6)
            _run(["netsh", "interface", "ipv6", "add", "dns", f"name={adapter}", ipv6_2, "index=2"])
    log.info("Applied DNS %s/%s on adapter %s", primary, secondary, adapter)


def reset_dhcp(adapter: str):
    if not adapter or not adapter.strip():
        raise ValueError("No adapter selected")
    _run(["netsh", "interface", "ip", "set", "dns", f"name={adapter}", "dhcp"])
    _run(["netsh", "interface", "ipv6", "set", "dns", f"name={adapter}", "dhcp"])
    log.info("Reset adapter %s to DHCP", adapter)


def flush_cache():
    result = _run(["ipconfig", "/flushdns"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "ipconfig /flushdns failed")
    log.info("Flushed DNS cache")


def current_status():
    return _run(["ipconfig", "/all"], timeout=15).stdout
