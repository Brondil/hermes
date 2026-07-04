import re
class TextCleaner:
    def clean(self, text: str) -> str:
        if not text: return ""
        text = re.sub(r'[^\w\s]', '', text)
        return " ".join(text.split())
