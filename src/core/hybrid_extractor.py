from .llm_operator import LLMOperator

class DeterministicExtractor:
    def extract_entities(self, text):
        # Placeholder: Replace with your existing regex/rule-based logic
        return {"characters": [], "locations": [], "events": [], "themes": []}

    def segment_text(self, text):
        # Placeholder: Replace with your existing segmentation logic
        return []

class HybridExtractor:
    def __init__(self, llm_operator: LLMOperator):
        self.llm = llm_operator
        self.det = DeterministicExtractor()

    def extract_entities(self, text, context=None):
        det_entities = self.det.extract_entities(text)
        llm_entities = self.llm.extract_entities(text, context)
        return self._merge_entities(det_entities, llm_entities)

    def segment_text(self, text, context=None):
        det_segments = self.det.segment_text(text)
        llm_segments = self.llm.segment_text(text, context)
        return self._merge_segments(det_segments, llm_segments)

    def _merge_entities(self, det, llm):
        # Simple union of entity lists for now
        merged = {}
        for key in ["characters", "locations", "events", "themes"]:
            det_list = det.get(key, [])
            llm_list = llm.get(key, []) if llm else []
            merged[key] = list({json.dumps(e, sort_keys=True) for e in det_list + llm_list})
            merged[key] = [json.loads(e) for e in merged[key]]
        return merged

    def _merge_segments(self, det, llm):
        # Simple union for now; can be improved
        if not det:
            return llm
        if not llm:
            return det
        # Merge by start index or text
        seen = set()
        merged = []
        for seg in det + llm:
            key = seg.get('start', '') if isinstance(seg, dict) else str(seg)
            if key not in seen:
                merged.append(seg)
                seen.add(key)
        return merged 