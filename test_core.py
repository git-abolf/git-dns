import pytest

from app.core.dns_engine import validate_dns
from app.platform.unix_dns import _validate_ips
from app.cli import build_parser


def test_ipv4():
    assert validate_dns('1.1.1.1', 4) == '1.1.1.1'


def test_ipv6():
    assert validate_dns('2606:4700:4700::1111', 6).startswith('2606:')


def test_validate_dns_rejects_wrong_version():
    with pytest.raises(ValueError):
        validate_dns('1.1.1.1', 6)


def test_unix_validate_ips_filters_blanks_and_normalizes():
    assert _validate_ips('1.1.1.1', '', '  8.8.8.8  ') == ['1.1.1.1', '8.8.8.8']


def test_unix_validate_ips_rejects_garbage():
    with pytest.raises(ValueError):
        _validate_ips('not-an-ip')


def test_cli_parser_requires_target_for_apply():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(['apply', '1.1.1.1'])  # missing --target


def test_cli_parser_apply_ok():
    parser = build_parser()
    args = parser.parse_args(['apply', '1.1.1.1', '1.0.0.1', '--target', 'Wi-Fi'])
    assert args.target == 'Wi-Fi'
    assert args.servers == ['1.1.1.1', '1.0.0.1']
