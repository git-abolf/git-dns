# PyInstaller spec for Windows. Run on Windows with PyInstaller installed.
from PyInstaller.utils.hooks import collect_submodules
hiddenimports = collect_submodules('app')

block_cipher = None

a = Analysis(['main.py'], pathex=['.'], binaries=[], datas=[('assets', 'assets')], hiddenimports=hiddenimports,
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['kivy'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='DNSMasterPro', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=True, console=False,
          icon='assets/icon.ico')
