"""
TraceLoop NLP Engine
Natural language processing for conversational data entry and querying
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

STAGES = [
    "collection", "segregation", "baling", "weighing", "washing",
    "qc_test", "recycling", "granulation", "dispatch", "receive"
]

MATERIAL_TYPES = ["PET", "HDPE", "PP", "LDPE", "PVC", "PS", "Mixed"]

INTENT_PATTERNS = {
    "purchase": [r"\b(purchased?|bought|procured?|buy|acquired?)\b"],
    "collection": [r"\b(collected?|collect|gather|pickup)\b"],
    "segregation": [r"\b(sorted?|sorting|segregat|separate|graded?)\b"],
    "baling": [r"\b(baled?|baling|bale|compressed?)\b"],
    "weighing": [r"\b(weighed?|weighing|weight|scale)\b"],
    "washing": [r"\b(washed?|washing|clean|cleaned?)\b"],
    "qc_test": [r"\b(qc|quality|test|inspected?|checked?)\b"],
    "recycling": [r"\b(recycl|processed?|processing|converted?)\b"],
    "granulation": [r"\b(granulat|shredded?|flakes?|pellet)\b"],
    "dispatch": [r"\b(dispatched?|dispatch|shipped?|sent|delivered?)\b"],
    "receive": [r"\b(received?|receive|arrival|arrived?)\b"],
    "query": [r"\b(show|how much|what|list|report|summary|total|average)\b"],
    "help": [r"\b(help|guide|how to|instructions?)\b"],
}

STATUS_KEYWORDS = {
    "approved": ["approved", "accepted", "passed", "ok", "good", "cleared"],
    "rejected": ["rejected", "failed", "declined", "not ok", "bad", "failed qc"],
    "cancelled": ["cancelled", "canceled", "void", "aborted"],
    "pending": ["pending", "in progress", "waiting", "ongoing"],
}

class NLPEngine:
    
    def __init__(self):
        self.context = {}
    
    def parse(self, text: str) -> Dict:
        text_lower = text.lower()
        
        intent = self._detect_intent(text_lower)
        entities = self._extract_entities(text, text_lower)
        
        return {
            "intent": intent,
            "entities": entities,
            "original_text": text,
            "confidence": self._calculate_confidence(intent, entities),
            "timestamp": datetime.now().isoformat()
        }
    
    def _detect_intent(self, text: str) -> str:
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return intent
        return "unknown"
    
    def _extract_entities(self, original: str, text_lower: str) -> Dict:
        entities = {
            "material_type": None,
            "quantity_kg": None,
            "quantity_pcs": None,
            "vendor": None,
            "buyer": None,
            "location": None,
            "actor": None,
            "status": None,
            "date": None,
            "batch_id": None,
            "grade": None,
            "loss_kg": None,
            "loss_percent": None,
        }
        
        qty_kg_pattern = r'(\d+(?:\.\d+)?)\s*(?:kg|kgs|kilogram|kilograms?)'
        match = re.search(qty_kg_pattern, text_lower)
        if match:
            entities["quantity_kg"] = float(match.group(1))
        
        qty_pcs_pattern = r'(\d+(?:\.\d+)?)\s*(?:pcs|pieces?|units?)'
        match = re.search(qty_pcs_pattern, text_lower)
        if match:
            entities["quantity_pcs"] = int(match.group(1))
        
        for mat in MATERIAL_TYPES:
            if mat.lower() in text_lower:
                entities["material_type"] = mat
                break
        
        vendor_patterns = [
            r'(?:from|vendor|supplier)\s+([A-Za-z][A-Za-z\s]{0,20}?)(?:\s+(?:yesterday|today|last|on|$))',
            r'vendor\s*[:=]?\s*([A-Za-z][A-Za-z\s]{1,15})',
        ]
        for pattern in vendor_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entities["vendor"] = match.group(1).strip().title()
                break
        
        buyer_patterns = [
            r'(?:to|buyer|customer)\s+([A-Za-z][A-Za-z\s]{0,20}?)(?:\s+(?:yesterday|today|last|on|$))',
        ]
        for pattern in buyer_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entities["buyer"] = match.group(1).strip().title()
                break
        
        batch_pattern = r'[Bb]-?(\d{2,4})'
        match = re.search(batch_pattern, original)
        if match:
            entities["batch_id"] = f"B-{match.group(1)}"
        
        for status, keywords in STATUS_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                entities["status"] = status.upper()
                break
        
        grade_pattern = r'\b(grade\s*)?[ABCD]\b'
        match = re.search(grade_pattern, original.upper())
        if match:
            entities["grade"] = match.group(0).replace("GRADE", "").strip()
        
        date = self._parse_date(text_lower)
        if date:
            entities["date"] = date
        
        loss_pattern = r'(\d+(?:\.\d+)?)\s*(?:kg|%)?\s*(?:loss|lost|waste)'
        match = re.search(loss_pattern, text_lower)
        if match:
            val = float(match.group(1))
            if "%" in text_lower:
                entities["loss_percent"] = val
            else:
                entities["loss_kg"] = val
        
        return entities
    
    def _parse_date(self, text: str) -> Optional[str]:
        today = datetime.now()
        
        if "today" in text:
            return today.strftime("%Y-%m-%d")
        if "yesterday" in text:
            return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        if "last week" in text:
            return (today - timedelta(weeks=1)).strftime("%Y-%m-%d")
        if "last month" in text:
            return (today - timedelta(days=30)).strftime("%Y-%m-%d")
        
        date_pattern = r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})'
        match = re.search(date_pattern, text)
        if match:
            day, month, year = match.groups()
            year = year if len(year) == 4 else f"20{year}"
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return None
    
    def _calculate_confidence(self, intent: str, entities: Dict) -> float:
        if intent == "unknown":
            return 0.0
        
        score = 0.3
        
        if entities.get("quantity_kg") or entities.get("quantity_pcs"):
            score += 0.25
        if entities.get("material_type"):
            score += 0.2
        if entities.get("vendor") or entities.get("buyer"):
            score += 0.15
        if entities.get("date"):
            score += 0.1
        
        return min(score, 1.0)
    
    def generate_response(self, parsed: Dict, action_result: Dict = None) -> str:
        intent = parsed["intent"]
        entities = parsed["entities"]
        
        if intent == "unknown":
            return "I couldn't understand that. Try something like: 'Purchased 300kg PET from GreenCorp yesterday' or 'Show all batches'"
        
        if intent == "query":
            if action_result:
                return action_result.get("message", "Here's what I found.")
            return "Let me look that up for you."
        
        if intent in ["purchase", "collection"]:
            qty = entities.get("quantity_kg", "?")
            mat = entities.get("material_type", "material")
            vendor = entities.get("vendor", "vendor")
            batch = action_result.get("batch_id", "new batch") if action_result else "new batch"
            return f"Got it! Recorded {qty}kg of {mat} from {vendor}. Batch ID: {batch}"
        
        if intent == "dispatch":
            qty = entities.get("quantity_kg", "?")
            buyer = entities.get("buyer", "customer")
            return f"Dispatch recorded: {qty}kg sent to {buyer}"
        
        if intent == "qc_test":
            status = entities.get("status", "PENDING")
            return f"QC Test recorded with status: {status}"
        
        return f"Recorded {intent} successfully."


class QueryParser:
    
    @staticmethod
    def parse_query(text: str) -> Dict:
        text_lower = text.lower()
        
        query_type = "general"
        filters = {}
        
        if "dispatched" in text_lower or "dispatch" in text_lower:
            query_type = "dispatch_summary"
        elif "loss" in text_lower or "waste" in text_lower:
            query_type = "loss_analysis"
        elif "efficiency" in text_lower or "yield" in text_lower:
            query_type = "efficiency_report"
        elif "vendor" in text_lower or "supplier" in text_lower:
            query_type = "vendor_analysis"
        elif "batch" in text_lower:
            query_type = "batch_list"
        
        if "last week" in text_lower:
            filters["date_range"] = "last_7_days"
        elif "last month" in text_lower:
            filters["date_range"] = "last_30_days"
        elif "this month" in text_lower:
            filters["date_range"] = "this_month"
        elif "today" in text_lower:
            filters["date_range"] = "today"
        
        for mat in MATERIAL_TYPES:
            if mat.lower() in text_lower:
                filters["material_type"] = mat
                break
        
        batch_pattern = r'[Bb]-?(\d{2,4})'
        import re
        match = re.search(batch_pattern, text)
        if match:
            filters["batch_id"] = f"B-{match.group(1)}"
        
        return {
            "query_type": query_type,
            "filters": filters,
            "original_text": text
        }
