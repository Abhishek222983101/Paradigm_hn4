"""
TraceLoop Unit Tests
Tests for NLP engine, database operations, and API endpoints
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.nlp_engine import NLPEngine, QueryParser
from backend.database import (
    init_database, get_connection, BatchRepository,
    TransactionRepository, ChatHistoryRepository
)


class TestNLPEngine:
    
    @pytest.fixture
    def nlp(self):
        return NLPEngine()
    
    def test_parse_purchase_intent(self, nlp):
        result = nlp.parse("Purchased 300kg PET from GreenCorp yesterday")
        
        assert result["intent"] == "purchase"
        assert result["entities"]["quantity_kg"] == 300
        assert result["entities"]["material_type"] == "PET"
        assert result["entities"]["vendor"] == "Greencorp"
        assert result["confidence"] > 0.5
    
    def test_parse_dispatch_intent(self, nlp):
        result = nlp.parse("Dispatched 500 kg to PlastiCo")
        
        assert result["intent"] == "dispatch"
        assert result["entities"]["quantity_kg"] == 500
        assert result["entities"]["buyer"] == "Plastico"
    
    def test_parse_query_intent(self, nlp):
        result = nlp.parse("Show all batches from last week")
        
        assert result["intent"] == "query"
    
    def test_parse_loss_intent(self, nlp):
        result = nlp.parse("Lost 50kg during processing")
        
        assert result["entities"]["loss_kg"] == 50
    
    def test_extract_material_types(self, nlp):
        materials = ["PET", "HDPE", "PP", "LDPE", "Mixed"]
        
        for mat in materials:
            result = nlp.parse(f"Received 100kg {mat} from vendor")
            assert result["entities"]["material_type"] == mat
    
    def test_extract_quantities(self, nlp):
        test_cases = [
            ("300kg", 300),
            ("500 kg", 500),
            ("1000kgs", 1000),
            ("250.5 kg", 250.5),
        ]
        
        for text, expected in test_cases:
            result = nlp.parse(f"Purchased {text} of material")
            assert result["entities"]["quantity_kg"] == expected
    
    def test_parse_date_today(self, nlp):
        from datetime import datetime
        result = nlp.parse("Purchased 100kg PET today")
        
        assert result["entities"]["date"] == datetime.now().strftime("%Y-%m-%d")
    
    def test_parse_date_yesterday(self, nlp):
        from datetime import datetime, timedelta
        result = nlp.parse("Purchased 100kg PET yesterday")
        
        expected = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        assert result["entities"]["date"] == expected
    
    def test_unknown_intent(self, nlp):
        result = nlp.parse("This is random text with no meaning")
        
        assert result["intent"] == "unknown"
    
    def test_generate_response_purchase(self, nlp):
        parsed = {"intent": "purchase", "entities": {"quantity_kg": 300, "material_type": "PET"}}
        action_result = {"batch_id": "B-101"}
        
        response = nlp.generate_response(parsed, action_result)
        
        assert "300" in response or "PET" in response or "B-101" in response


class TestQueryParser:
    
    @pytest.fixture
    def parser(self):
        return QueryParser()
    
    def test_parse_dispatch_query(self, parser):
        result = parser.parse_query("How much material was dispatched last week?")
        
        assert result["query_type"] == "dispatch_summary"
        assert result["filters"]["date_range"] == "last_7_days"
    
    def test_parse_loss_query(self, parser):
        result = parser.parse_query("Show me losses this month")
        
        assert result["query_type"] == "loss_analysis"
    
    def test_parse_batch_query(self, parser):
        result = parser.parse_query("Show batch B-101")
        
        assert result["query_type"] == "batch_list"
        assert result["filters"]["batch_id"] == "B-101"
    
    def test_parse_material_filter(self, parser):
        result = parser.parse_query("Show all PET batches")
        
        assert result["filters"]["material_type"] == "PET"


class TestDatabase:
    
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        test_db = tmp_path / "test_traceloop.db"
        self.original_db = None
        from backend import database
        self.original_db = database.DB_PATH
        database.DB_PATH = str(test_db)
        init_database()
        yield
        database.DB_PATH = self.original_db
    
    def test_create_batch(self):
        batch = BatchRepository.create(
            batch_id="TEST-001",
            material_type="PET",
            source_vendor="TestVendor"
        )
        
        assert batch["batch_id"] == "TEST-001"
        assert batch["material_type"] == "PET"
    
    def test_get_batch(self):
        BatchRepository.create(
            batch_id="TEST-002",
            material_type="HDPE",
            source_vendor="TestVendor"
        )
        
        batch = BatchRepository.get("TEST-002")
        
        assert batch is not None
        assert batch["material_type"] == "HDPE"
    
    def test_get_nonexistent_batch(self):
        batch = BatchRepository.get("NONEXISTENT")
        
        assert batch is None
    
    def test_create_transaction(self):
        BatchRepository.create(
            batch_id="TEST-003",
            material_type="PP",
            source_vendor="TestVendor"
        )
        
        tx = TransactionRepository.create(
            transaction_id="TX-001",
            batch_id="TEST-003",
            stage="collection",
            qty_in=500,
            status="APPROVED"
        )
        
        assert tx["transaction_id"] == "TX-001"
        assert tx["batch_id"] == "TEST-003"
    
    def test_get_transactions_by_batch(self):
        BatchRepository.create(
            batch_id="TEST-004",
            material_type="PET"
        )
        
        TransactionRepository.create(
            transaction_id="TX-002",
            batch_id="TEST-004",
            stage="collection",
            qty_in=300
        )
        TransactionRepository.create(
            transaction_id="TX-003",
            batch_id="TEST-004",
            stage="sorting",
            qty_in=300,
            qty_out=270
        )
        
        transactions = TransactionRepository.get_by_batch("TEST-004")
        
        assert len(transactions) == 2
    
    def test_chat_history_logging(self):
        ChatHistoryRepository.log(
            user_input="Test input",
            intent="purchase",
            entities={"quantity_kg": 100},
            response="Test response"
        )
        
        history = ChatHistoryRepository.get_recent(limit=10)
        
        assert len(history) >= 1
        assert history[0]["user_input"] == "Test input"


class TestConfidenceScore:
    
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        from backend import database
        self.original_db = database.DB_PATH
        database.DB_PATH = str(tmp_path / "test.db")
        init_database()
        yield
        database.DB_PATH = self.original_db
    
    def test_confidence_increases_with_stages(self):
        BatchRepository.create(
            batch_id="CONF-001",
            material_type="PET"
        )
        
        confidence_0 = BatchRepository.calculate_confidence("CONF-001")
        
        TransactionRepository.create(
            transaction_id="TX-C1",
            batch_id="CONF-001",
            stage="collection",
            qty_in=500
        )
        
        confidence_1 = BatchRepository.calculate_confidence("CONF-001")
        
        TransactionRepository.create(
            transaction_id="TX-C2",
            batch_id="CONF-001",
            stage="sorting",
            qty_in=500
        )
        
        confidence_2 = BatchRepository.calculate_confidence("CONF-001")
        
        assert confidence_2 > confidence_1 > confidence_0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
