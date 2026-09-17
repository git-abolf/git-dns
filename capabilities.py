import os
import platform


def capabilities():
    system = platform.system()
    is_android = system == "Android" or bool(os.environ.get("ANDROID_ARGUMENT"))

    unix_dns_control = False
    if system in ("Linux", "Darwin"):
        try:
            from app.platform.unix_dns import is_supported
            unix_dns_control = is_supported()
        except ImportError:
            unix_dns_control = False

    return {
        "platform": system,
        "windows_dns_control": system == "Windows",
        "linux_dns_control": system == "Linux" and unix_dns_control,
        "macos_dns_control": system == "Darwin" and unix_dns_control,
        "android": is_android,
        # Android has no real system/Private DNS backend yet — benchmarking
        # only, tracked in CHANGELOG.md.
        "android_dns_control": False,
        "ipv4": True,
        "ipv6": True,
        "doh": True,
        "dot": True,
        "vpn": system in ("Windows", "Android"),
    }
