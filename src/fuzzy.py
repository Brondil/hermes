class FuzzyHashSet:
    def __init__(self, threshold=0.8):
        self.items = []
        self.threshold = threshold

    def add(self, text: str) -> (bool, bool):
        text = text.lower().strip()
        if not text: return False, False
        for existing_text in self.items:
            if self._is_similar(text, existing_text):
                return False, True
        self.items.append(text)
        return True, False

    def _is_similar(self, s1, s2):
        set1 = set(s1)
        set2 = set(s2)
        union = len(set1 | set2)
        if union == 0: return True
        intersection = len(set1 & set2)
        return (intersection / union) >= self.threshold

    def reset(self):
        self.items = []
