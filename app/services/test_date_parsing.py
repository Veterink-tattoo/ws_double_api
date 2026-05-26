import unittest
from datetime import datetime, timezone
import sys
import os

# Adiciona o diretório base ao sys.path para permitir importações corretas de app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.core.date_utils import parse_created_at

class TestDateParsing(unittest.TestCase):
    def test_valid_iso_with_z(self):
        date_str = "2026-05-08T19:59:42.082Z"
        expected = datetime.fromisoformat("2026-05-08T19:59:42.082")
        result = parse_created_at(date_str)
        self.assertEqual(result, expected)

    def test_valid_iso_without_z(self):
        date_str = "2026-05-08T19:59:42.082"
        expected = datetime.fromisoformat("2026-05-08T19:59:42.082")
        result = parse_created_at(date_str)
        self.assertEqual(result, expected)

    def test_none_date_fallback(self):
        before = datetime.utcnow()
        result = parse_created_at(None)
        after = datetime.utcnow()
        self.assertTrue(before <= result <= after)

    def test_invalid_date_fallback(self):
        before = datetime.utcnow()
        result = parse_created_at("not-a-date")
        after = datetime.utcnow()
        self.assertTrue(before <= result <= after)

if __name__ == "__main__":
    unittest.main()
