import os, platform

IS_ANDROID = bool(os.environ.get("ANDROID_ARGUMENT")) or platform.system() == "Android"

if IS_ANDROID:
    from app.mobile.mobile_app import DNSMasterMobileApp
    DNSMasterMobileApp().run()
elif platform.system() == "Windows":
    from app.desktop.desktop_app import DNSMasterFinal
    DNSMasterFinal().mainloop()
else:
    try:
        from app.mobile.mobile_app import DNSMasterMobileApp
        DNSMasterMobileApp().run()
    except ImportError:
        raise SystemExit("Install Kivy for the cross-platform desktop/mobile fallback: pip install kivy")
