"""DNS Master Pro — cross-platform command-line interface.

Unlike the GUI (Windows-only) and the Kivy mobile app (test-only on
Android), this CLI performs *real* DNS switching on Windows, Linux and
macOS from one codebase, using the hardened platform backends.

Examples:
    python -m app.cli benchmark 1.1.1.1 8.8.8.8 9.9.9.9
    python -m app.cli list-targets
    python -m app.cli apply --target "Wi-Fi" 1.1.1.1 1.0.0.1
    python -m app.cli reset --target "Wi-Fi"
    python -m app.cli flush
"""
import argparse
import platform
import sys

from app.core.dns_engine import benchmark_many
from app.core.logger import get_logger

log = get_logger("cli")

PRESETS = {
    "cloudflare": ["1.1.1.1", "1.0.0.1"],
    "google": ["8.8.8.8", "8.8.4.4"],
    "quad9": ["9.9.9.9", "149.112.112.112"],
    "shecan": ["178.22.122.100", "185.51.200.2"],
}


def _backend():
    system = platform.system()
    if system == "Windows":
        from app.platform import windows_dns as backend
    elif system in ("Linux", "Darwin"):
        from app.platform import unix_dns as backend
    else:
        print(f"Unsupported platform: {system}", file=sys.stderr)
        sys.exit(1)
    return backend, system


def cmd_benchmark(args):
    servers = args.servers or [ip for group in PRESETS.values() for ip in group]
    results = benchmark_many(servers, attempts=args.attempts)
    print(f"{'Server':<20}{'Avg ms':>10}{'Reliability':>14}{'Score':>8}")
    for r in results:
        print(f"{r.server:<20}{(r.average_ms or 0):>10.1f}{r.reliability:>13.1f}%{r.score:>8.1f}")


def cmd_list_targets(args):
    backend, system = _backend()
    if system == "Windows":
        targets = backend.list_adapters()
    elif system == "Linux":
        targets = backend.linux_list_connections()
    else:
        targets = backend.macos_list_services()
    if not targets:
        print("No active network targets found (or the required OS DNS tool is missing).")
        return
    for t in targets:
        print(t)


def cmd_apply(args):
    backend, system = _backend()
    servers = args.servers
    if not servers:
        print("Provide at least one DNS server IP.", file=sys.stderr)
        sys.exit(1)
    try:
        if system == "Windows":
            secondary = servers[1] if len(servers) > 1 else ""
            backend.apply_dns(args.target, servers[0], secondary)
        elif system == "Linux":
            backend.linux_apply_dns(args.target, servers)
        else:
            backend.macos_apply_dns(args.target, servers)
        print(f"Applied {servers} to {args.target!r}.")
    except Exception as exc:
        log.exception("apply failed")
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_reset(args):
    backend, system = _backend()
    try:
        if system == "Windows":
            backend.reset_dhcp(args.target)
        elif system == "Linux":
            backend.linux_reset_dhcp(args.target)
        else:
            backend.macos_reset_dhcp(args.target)
        print(f"{args.target!r} reset to DHCP-assigned DNS.")
    except Exception as exc:
        log.exception("reset failed")
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_flush(args):
    backend, system = _backend()
    try:
        if system == "Windows":
            backend.flush_cache()
        elif system == "Linux":
            backend.linux_flush_cache()
        else:
            backend.macos_flush_cache()
        print("DNS cache flushed.")
    except Exception as exc:
        log.exception("flush failed")
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)


def build_parser():
    p = argparse.ArgumentParser(prog="dnsmasterpro", description="DNS Master Pro CLI")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("benchmark", help="Benchmark DNS servers by latency/reliability")
    b.add_argument("servers", nargs="*", help="IPs to test (default: all presets)")
    b.add_argument("--attempts", type=int, default=4)
    b.set_defaults(func=cmd_benchmark)

    lt = sub.add_parser("list-targets", help="List adapters/connections/services to apply DNS to")
    lt.set_defaults(func=cmd_list_targets)

    a = sub.add_parser("apply", help="Apply DNS servers to a network target")
    a.add_argument("servers", nargs="+", help="Primary [secondary] IPs")
    a.add_argument("--target", required=True, help="Adapter (Windows), connection (Linux) or service (macOS)")
    a.set_defaults(func=cmd_apply)

    r = sub.add_parser("reset", help="Reset a target back to DHCP-assigned DNS")
    r.add_argument("--target", required=True)
    r.set_defaults(func=cmd_reset)

    f = sub.add_parser("flush", help="Flush the local DNS resolver cache")
    f.set_defaults(func=cmd_flush)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
