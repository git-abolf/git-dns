import os, threading
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from app.core.dns_engine import benchmark
from app.core.storage import load, save, SETTINGS
from app.core.ai import OnlineAI

KV = '''
#:import dp kivy.metrics.dp
<Root>:
    orientation: 'vertical'
    padding: dp(14)
    spacing: dp(10)
    Label:
        text: 'DNS Master Pro'
        font_size: '25sp'
        size_hint_y: None
        height: dp(50)
    Label:
        text: root.status
        size_hint_y: None
        height: dp(40)
    TextInput:
        id: dns
        text: '1.1.1.1'
        hint_text: 'IPv4 DNS'
        multiline: False
        size_hint_y: None
        height: dp(48)
    BoxLayout:
        size_hint_y: None
        height: dp(48)
        spacing: dp(8)
        Button:
            text: 'Test DNS'
            on_release: root.test_dns(dns.text)
        Button:
            text: 'Restore'
            on_release: root.restore()
    Button:
        text: 'Online AI'
        size_hint_y: None
        height: dp(48)
        on_release: root.ask_ai()
    ScrollView:
        Label:
            text: root.output
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1] + dp(20)
            halign: 'left'
            valign: 'top'
'''

class Root(BoxLayout):
    status = StringProperty('Ready')
    output = StringProperty('Portable mobile mode. DNS testing works without root.\n')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = load(SETTINGS, {"sound": True, "theme": "blue", "ai_model": "gpt-5.5"})

    def test_dns(self, server):
        self.status = 'Testing...'
        def worker():
            try:
                result = benchmark(server, attempts=4)
                text = (f'DNS: {result.server}\\nProtocol: {result.protocol}\\n'
                        f'Average: {result.average_ms} ms\\nMin: {result.min_ms} ms\\n'
                        f'Max: {result.max_ms} ms\\nReliability: {result.reliability}%\\n'
                        f'Score: {result.score}/100')
            except Exception as e:
                text = f'Error: {e}'
            from kivy.clock import Clock
            Clock.schedule_once(lambda *_: self._result(text), 0)
        threading.Thread(target=worker, daemon=True).start()

    def _result(self, text):
        self.output = text
        self.status = 'Finished'

    def restore(self):
        self.status = 'Restore is platform dependent.'
        self.output = 'Android does not allow an ordinary Python app to change system DNS without a supported VPN/private-DNS mechanism.\\nThe mobile build therefore never pretends a DNS change succeeded.'

    def ask_ai(self):
        key = os.environ.get('OPENAI_API_KEY', '')
        if not key:
            self._result('Set OPENAI_API_KEY in the Android app environment or connect your own secure backend. Do not hard-code an API key in the APK.')
            return
        self.status = 'AI...'
        def worker():
            try:
                text = OnlineAI(key, self.settings.get('ai_model', 'gpt-5.5')).ask('Give a concise DNS troubleshooting checklist for a mobile user.')
            except Exception as e:
                text = str(e)
            from kivy.clock import Clock
            Clock.schedule_once(lambda *_: self._result(text), 0)
        threading.Thread(target=worker, daemon=True).start()

class DNSMasterMobileApp(App):
    def build(self):
        return Builder.load_string(KV)
