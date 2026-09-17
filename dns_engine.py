import asyncio
import ipaddress
import socket
import statistics
import time
from dataclasses import dataclass, asdict
from typing import Optional

DEFAULT_DOMAINS = ["example.com", "cloudflare.com", "google.com", "github.com"]

@dataclass
class DNSResult:
    server: str
    protocol: str = "IPv4"
    success: int = 0
    failures: int = 0
    samples_ms: list = None
    error: str = ""

    def __post_init__(self):
        if self.samples_ms is None:
            self.samples_ms = []

    @property
    def average_ms(self):
        return round(statistics.mean(self.samples_ms), 2) if self.samples_ms else None

    @property
    def min_ms(self):
        return round(min(self.samples_ms), 2) if self.samples_ms else None

    @property
    def max_ms(self):
        return round(max(self.samples_ms), 2) if self.samples_ms else None

    @property
    def reliability(self):
        total = self.success + self.failures
        return round(self.success / total * 100, 1) if total else 0.0

    @property
    def score(self):
        if not self.samples_ms and not self.success:
            return 0
        latency = self.average_ms or 999
        latency_score = max(0, min(100, 100 - latency))
        return round(0.55 * latency_score + 0.45 * self.reliability, 1)

    def to_dict(self):
        d = asdict(self)
        d.update(average_ms=self.average_ms, min_ms=self.min_ms, max_ms=self.max_ms,
                 reliability=self.reliability, score=self.score)
        return d


def validate_dns(value: str, version: Optional[int] = None) -> str:
    value = value.strip()
    ip = ipaddress.ip_address(value)
    if version and ip.version != version:
        raise ValueError(f"Expected IPv{version}")
    return str(ip)


def _query(server: str, domain: str, timeout: float = 2.0) -> float:
    # Portable DNS reachability/latency test using the system resolver path is
    # intentionally not used: this measures TCP/UDP DNS directly when dnspython
    # is available, otherwise it falls back to a normal socket resolution.
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [server]
        resolver.timeout = timeout
        resolver.lifetime = timeout
        started = time.perf_counter()
        resolver.resolve(domain, "A", raise_on_no_answer=False)
        return (time.perf_counter() - started) * 1000
    except ImportError:
        started = time.perf_counter()
        socket.setdefaulttimeout(timeout)
        socket.getaddrinfo(domain, 443, type=socket.SOCK_STREAM)
        return (time.perf_counter() - started) * 1000


def benchmark(server: str, attempts: int = 4, domains=None, timeout: float = 2.0) -> DNSResult:
    server = validate_dns(server)
    result = DNSResult(server=server, protocol=f"IPv{ipaddress.ip_address(server).version}")
    domains = domains or DEFAULT_DOMAINS
    for i in range(max(1, attempts)):
        domain = domains[i % len(domains)]
        try:
            result.samples_ms.append(round(_query(server, domain, timeout), 2))
            result.success += 1
        except Exception as exc:
            result.failures += 1
            result.error = str(exc)[:180]
    return result


def benchmark_many(servers, attempts=4, domains=None, timeout=2.0):
    results = []
    for server in servers:
        try:
            results.append(benchmark(server, attempts, domains, timeout))
        except Exception as exc:
            results.append(DNSResult(server=str(server), error=str(exc)[:180], failures=1))
    return sorted(results, key=lambda x: (-x.score, x.average_ms or 9999))
