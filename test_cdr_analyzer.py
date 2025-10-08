#!/usr/bin/env python3
"""
Tests for CDR Analyzer
"""

import unittest
import os
import sys
from cdr_analyzer import CDRRecord, CDRAnalyzer


class TestCDRRecord(unittest.TestCase):
    """Test CDRRecord class"""
    
    def test_create_record(self):
        """Test creating a CDR record"""
        record = CDRRecord(
            caller="+1234567890",
            recipient="+1987654321",
            call_type="voice",
            duration=120,
            timestamp="2024-01-15 09:30:00",
            cost=0.50
        )
        self.assertEqual(record.caller, "+1234567890")
        self.assertEqual(record.recipient, "+1987654321")
        self.assertEqual(record.call_type, "voice")
        self.assertEqual(record.duration, 120)
        self.assertEqual(record.cost, 0.50)


class TestCDRAnalyzer(unittest.TestCase):
    """Test CDRAnalyzer class"""
    
    def setUp(self):
        """Set up test analyzer with sample data"""
        self.analyzer = CDRAnalyzer()
        
        # Add sample records manually
        self.analyzer.records = [
            CDRRecord("+1234567890", "+1987654321", "voice", 120, "2024-01-15 09:30:00", 0.50),
            CDRRecord("+1234567890", "+1555123456", "sms", 0, "2024-01-15 09:35:00", 0.10),
            CDRRecord("+1987654321", "+1234567890", "voice", 300, "2024-01-15 10:00:00", 1.25),
            CDRRecord("+1555123456", "+1234567890", "voice", 180, "2024-01-15 10:30:00", 0.75),
        ]
    
    def test_total_calls(self):
        """Test getting total number of calls"""
        self.assertEqual(self.analyzer.get_total_calls(), 4)
    
    def test_calls_by_type(self):
        """Test getting calls by type"""
        calls_by_type = self.analyzer.get_calls_by_type()
        self.assertEqual(calls_by_type['voice'], 3)
        self.assertEqual(calls_by_type['sms'], 1)
    
    def test_total_duration(self):
        """Test getting total duration of voice calls"""
        total = self.analyzer.get_total_duration()
        self.assertEqual(total, 600)  # 120 + 300 + 180
    
    def test_total_cost(self):
        """Test getting total cost"""
        total = self.analyzer.get_total_cost()
        self.assertAlmostEqual(total, 2.60, places=2)  # 0.50 + 0.10 + 1.25 + 0.75
    
    def test_calls_by_caller(self):
        """Test getting calls by caller"""
        calls_by_caller = self.analyzer.get_calls_by_caller()
        self.assertEqual(calls_by_caller['+1234567890'], 2)
        self.assertEqual(calls_by_caller['+1987654321'], 1)
        self.assertEqual(calls_by_caller['+1555123456'], 1)
    
    def test_top_callers(self):
        """Test getting top callers"""
        top_callers = self.analyzer.get_top_callers(2)
        self.assertEqual(len(top_callers), 2)
        self.assertEqual(top_callers[0][0], '+1234567890')
        self.assertEqual(top_callers[0][1], 2)
    
    def test_average_call_duration(self):
        """Test getting average call duration"""
        avg = self.analyzer.get_average_call_duration()
        self.assertEqual(avg, 200.0)  # (120 + 300 + 180) / 3
    
    def test_generate_report(self):
        """Test report generation"""
        report = self.analyzer.generate_report()
        self.assertIn("CDR ANALYSIS REPORT", report)
        self.assertIn("Total Records: 4", report)
        self.assertIn("Total Cost:", report)
    
    def test_load_from_csv(self):
        """Test loading from CSV file"""
        analyzer = CDRAnalyzer()
        test_file = "sample_cdr.csv"
        
        if os.path.exists(test_file):
            analyzer.load_from_csv(test_file)
            self.assertGreater(analyzer.get_total_calls(), 0)


if __name__ == '__main__':
    unittest.main()
