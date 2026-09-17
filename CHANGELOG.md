# Changelog

## Unreleased — theming pass
### Added
- Theme colors expanded from 10 to 50, including white, black, and a full spread of grays/reds/oranges/yellows/greens/teals/blues/purples/browns.
- A real "custom color" picker in Settings (`tkinter.colorchooser`) — pick literally any color, not just the 50 presets; it's saved and restored across restarts.

### Fixed
- `darken()` used to be a no-op (`return hex_color`), so every themed button's hover color was identical to its normal color — hover had no visible feedback. It now actually darkens.
- Added a matching `lighten()` for hover/border feedback on very dark accents (e.g. black), where darkening further does nothing.
- Added contrast-aware text color (`contrast_text()`) so button labels stay readable regardless of how light or dark the chosen accent is (e.g. dark text on white, white text on black).
- Themed buttons now get a 1px border derived from the accent; without it, a black or near-black accent used to visually disappear into the app's near-black background.

## v15.0.0 — Release hardening pass

### Added
- App icon and branding (`assets/icon.ico`, `assets/icon.png`, `assets/tray_icon.png`), wired into the Windows build (`DNSMasterPro.spec`), the Inno Setup installer, and the Android build (`buildozer.spec`). The window and tray now use the real icon instead of a placeholder drawn at runtime.
- `app/core/logger.py`: rotating file logger (`dnsmasterpro.log` in the per-OS app-data folder) shared by desktop, mobile and CLI. Replaces several silent `except: pass` blocks that used to swallow real errors.
- `app/platform/windows_dns.py`: Windows DNS backend extracted out of the UI, using argument-list `subprocess` calls (`shell=False`) and IP validation instead of building shell strings with f-strings.
- `app/platform/unix_dns.py`: **new** — real DNS switching on Linux (`nmcli`/`resolvectl`) and macOS (`networksetup`), not just benchmarking. Desktop DNS control is now genuinely cross-platform, not Windows-only.
- `app/cli.py`: a headless, cross-platform CLI (`python -m app.cli benchmark|list-targets|apply|reset|flush`) that works on Windows, Linux and macOS from one codebase — useful for power users, servers, and scripting.
- One-time in-app privacy notice before the first Online AI request, explaining that the prompt is sent to OpenAI's servers.
- `LICENSE` (MIT) and this changelog.

### Changed
- `desktop_app.py` version string corrected from `14.0` to `15.0.0` to match the installer, `buildozer.spec`, and the release zip name (previously inconsistent across files).
- `apply_dns`, `flush`, `reset_dhcp`, `refresh_adapters`, `show_current_dns`, and `copy_status` now go through the hardened `windows_dns` backend and log failures instead of failing silently.

### Known limitations (tracked, not yet done)
- The Windows `.exe` is still unsigned — expect SmartScreen warnings until a code-signing certificate is added to the build pipeline.
- `locales/en.json` / `fa.json` exist but the desktop UI strings are still hardcoded in Persian; full i18n wiring is future work.
- Android has no real system/Private DNS backend yet (`app/platform/android.py` is a planned stub) — the mobile app only benchmarks DNS servers, it cannot apply them at the OS level.
- Auto-update only checks GitHub Releases and shows a download link; it does not download/install automatically.
