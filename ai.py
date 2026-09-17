import json, os, urllib.request, urllib.error

class OnlineAI:
    def __init__(self, api_key=None, model="gpt-5.5"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model

    def ask(self, prompt, timeout=30):
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        payload = {"model": self.model, "input": prompt}
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"AI HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"AI network error: {exc.reason}") from exc
        text = data.get("output_text")
        if text:
            return text
        # Defensive fallback for response shapes.
        chunks = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("text"):
                    chunks.append(content["text"])
        return "\n".join(chunks).strip() or "No text returned by AI."
