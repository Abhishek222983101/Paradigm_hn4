"""
TraceLoop AI Service
Integration with Featherless.ai for enhanced NLP capabilities
"""

import os
import json
import re
from typing import Dict, Optional, List
from datetime import datetime
import httpx

FEATHERLESS_API_KEY = os.getenv("FEATHERLESS_API_KEY", "")
FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"

class AIService:
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or FEATHERLESS_API_KEY
        self.enabled = bool(self.api_key)
        self.model = "phi-3-mini"
    
    async def classify_intent(self, text: str) -> Dict:
        if not self.enabled:
            return self._fallback_intent_classification(text)
        
        prompt = f"""Classify the intent of this text related to recycling material tracking.

Text: "{text}"

Possible intents: purchase, collection, segregation, baling, washing, qc_test, recycling, granulation, dispatch, receive, query, help, unknown

Respond with JSON only:
{{"intent": "<intent>", "confidence": <0.0-1.0>}}"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{FEATHERLESS_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 100
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                    result = self._parse_json_response(content)
                    return {
                        "intent": result.get("intent", "unknown"),
                        "confidence": result.get("confidence", 0.5)
                    }
        except Exception as e:
            print(f"AI service error: {e}")
        
        return self._fallback_intent_classification(text)
    
    def _fallback_intent_classification(self, text: str) -> Dict:
        text_lower = text.lower()
        
        intent_keywords = {
            "purchase": ["purchased", "bought", "procured", "buy"],
            "collection": ["collected", "collect", "pickup"],
            "segregation": ["sorted", "sorting", "segregate"],
            "washing": ["washed", "washing", "clean"],
            "qc_test": ["qc", "quality", "test", "inspect"],
            "recycling": ["recycl", "process"],
            "dispatch": ["dispatched", "dispatch", "shipped", "sent"],
            "query": ["show", "how much", "what", "list", "report"],
            "help": ["help", "guide", "how to"],
        }
        
        for intent, keywords in intent_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return {"intent": intent, "confidence": 0.75}
        
        return {"intent": "unknown", "confidence": 0.0}
    
    async def extract_entities(self, text: str) -> Dict:
        if not self.enabled:
            return self._fallback_entity_extraction(text)
        
        prompt = f"""Extract entities from this recycling transaction text.

Text: "{text}"

Extract these entities if present:
- material_type: PET, HDPE, PP, LDPE, PVC, PS, or Mixed
- quantity_kg: number in kilograms
- vendor: supplier name
- buyer: customer name
- batch_id: batch identifier like B-101
- status: APPROVED, REJECTED, PENDING
- date: date if mentioned

Respond with JSON only:
{{"entities": {{"material_type": null, "quantity_kg": null, "vendor": null, "buyer": null, "batch_id": null, "status": null, "date": null}}}}"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{FEATHERLESS_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 200
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                    result = self._parse_json_response(content)
                    return result.get("entities", {})
        except Exception as e:
            print(f"AI service error: {e}")
        
        return self._fallback_entity_extraction(text)
    
    def _fallback_entity_extraction(self, text: str) -> Dict:
        entities = {
            "material_type": None,
            "quantity_kg": None,
            "vendor": None,
            "buyer": None,
            "batch_id": None,
            "status": None,
            "date": None
        }
        
        materials = ["PET", "HDPE", "PP", "LDPE", "PVC", "PS", "Mixed"]
        for mat in materials:
            if mat.lower() in text.lower():
                entities["material_type"] = mat
                break
        
        qty_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kg|kgs|kilogram)', text.lower())
        if qty_match:
            entities["quantity_kg"] = float(qty_match.group(1))
        
        vendor_match = re.search(r'(?:from|vendor)\s+([A-Za-z][A-Za-z\s]{1,20})', text.lower())
        if vendor_match:
            entities["vendor"] = vendor_match.group(1).strip().title()
        
        batch_match = re.search(r'[Bb]-?(\d{2,4})', text)
        if batch_match:
            entities["batch_id"] = f"B-{batch_match.group(1)}"
        
        if "approved" in text.lower():
            entities["status"] = "APPROVED"
        elif "rejected" in text.lower():
            entities["status"] = "REJECTED"
        
        return entities
    
    async def generate_insight(self, batch_data: Dict) -> str:
        if not self.enabled:
            return self._fallback_insight(batch_data)
        
        prompt = f"""Analyze this recycling batch data and generate a brief insight.

Batch: {batch_data.get('batch_id')}
Material: {batch_data.get('material_type')}
Input: {batch_data.get('total_input_kg')} kg
Output: {batch_data.get('total_output_kg')} kg
Vendor: {batch_data.get('source_vendor')}
Confidence: {batch_data.get('confidence_score')}%

Generate a 2-3 sentence insight about this batch's performance."""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{FEATHERLESS_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 150
                    },
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return content.strip()
        except Exception as e:
            print(f"AI service error: {e}")
        
        return self._fallback_insight(batch_data)
    
    def _fallback_insight(self, batch_data: Dict) -> str:
        batch_id = batch_data.get('batch_id', 'Unknown')
        material = batch_data.get('material_type', 'material')
        input_kg = batch_data.get('total_input_kg', 0)
        output_kg = batch_data.get('total_output_kg', 0)
        vendor = batch_data.get('source_vendor', 'Unknown')
        confidence = batch_data.get('confidence_score', 0)
        
        loss = input_kg - output_kg if input_kg and output_kg else 0
        loss_pct = (loss / input_kg * 100) if input_kg else 0
        
        insight = f"Batch {batch_id} ({material}): "
        insight += f"Started with {input_kg}kg from {vendor}. "
        
        if output_kg:
            insight += f"Final output: {output_kg}kg with {loss_pct:.1f}% loss. "
            if loss_pct > 25:
                insight += "Loss rate above average threshold."
            else:
                insight += "Performance within acceptable range."
        else:
            insight += "Processing not yet complete."
        
        return insight
    
    async def suggest_action(self, context: Dict) -> Dict:
        if not self.enabled:
            return {"suggestion": "Continue processing as normal."}
        
        prompt = f"""Based on this recycling operation context, suggest the next best action.

Context:
- Total batches: {context.get('total_batches', 0)}
- Average yield: {context.get('average_yield', 0)}%
- High loss batches: {context.get('high_loss_count', 0)}
- Pending QC: {context.get('pending_qc', 0)}

Suggest one specific action to improve operations. Respond with JSON:
{{"action": "<action>", "priority": "high|medium|low", "reason": "<why>"}}"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{FEATHERLESS_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.5,
                        "max_tokens": 150
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                    return self._parse_json_response(content)
        except Exception as e:
            print(f"AI service error: {e}")
        
        return {"suggestion": "Continue processing as normal."}
    
    def _parse_json_response(self, text: str) -> Dict:
        try:
            clean = re.sub(r'```(?:json)?', '', text).replace('```', '').strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            return {}


ai_service = AIService()
