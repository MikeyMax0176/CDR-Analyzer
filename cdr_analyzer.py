#!/usr/bin/env python3
"""
CDR Analyzer - A program to analyze call detail records
"""

import csv
import sys
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any


class CDRRecord:
    """Represents a single Call Detail Record"""
    
    def __init__(self, caller: str, recipient: str, call_type: str, 
                 duration: int, timestamp: str, cost: float = 0.0):
        self.caller = caller
        self.recipient = recipient
        self.call_type = call_type  # voice, sms, data
        self.duration = duration  # in seconds for voice, bytes for data
        self.timestamp = timestamp
        self.cost = cost
    
    def __repr__(self):
        return (f"CDRRecord(caller={self.caller}, recipient={self.recipient}, "
                f"type={self.call_type}, duration={self.duration}, "
                f"timestamp={self.timestamp}, cost={self.cost})")


class CDRAnalyzer:
    """Analyzes Call Detail Records"""
    
    def __init__(self):
        self.records: List[CDRRecord] = []
    
    def load_from_csv(self, filename: str) -> None:
        """Load CDR records from a CSV file"""
        try:
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    record = CDRRecord(
                        caller=row['caller'],
                        recipient=row['recipient'],
                        call_type=row['type'],
                        duration=int(row['duration']),
                        timestamp=row['timestamp'],
                        cost=float(row.get('cost', 0.0))
                    )
                    self.records.append(record)
            print(f"Loaded {len(self.records)} records from {filename}")
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading file: {e}")
            sys.exit(1)
    
    def get_total_calls(self) -> int:
        """Get total number of calls"""
        return len(self.records)
    
    def get_calls_by_type(self) -> Dict[str, int]:
        """Get count of calls by type"""
        calls_by_type = defaultdict(int)
        for record in self.records:
            calls_by_type[record.call_type] += 1
        return dict(calls_by_type)
    
    def get_total_duration(self) -> int:
        """Get total duration of all voice calls in seconds"""
        total = 0
        for record in self.records:
            if record.call_type == 'voice':
                total += record.duration
        return total
    
    def get_total_cost(self) -> float:
        """Get total cost of all calls"""
        return sum(record.cost for record in self.records)
    
    def get_calls_by_caller(self) -> Dict[str, int]:
        """Get count of calls by caller"""
        calls_by_caller = defaultdict(int)
        for record in self.records:
            calls_by_caller[record.caller] += 1
        return dict(calls_by_caller)
    
    def get_top_callers(self, n: int = 10) -> List[tuple]:
        """Get top N callers by number of calls"""
        calls_by_caller = self.get_calls_by_caller()
        sorted_callers = sorted(calls_by_caller.items(), 
                               key=lambda x: x[1], reverse=True)
        return sorted_callers[:n]
    
    def get_average_call_duration(self) -> float:
        """Get average duration of voice calls"""
        voice_calls = [r for r in self.records if r.call_type == 'voice']
        if not voice_calls:
            return 0.0
        total_duration = sum(r.duration for r in voice_calls)
        return total_duration / len(voice_calls)
    
    def generate_report(self) -> str:
        """Generate a comprehensive analysis report"""
        report = []
        report.append("=" * 60)
        report.append("CDR ANALYSIS REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Summary statistics
        report.append("SUMMARY STATISTICS")
        report.append("-" * 60)
        report.append(f"Total Records: {self.get_total_calls()}")
        report.append(f"Total Cost: ${self.get_total_cost():.2f}")
        report.append("")
        
        # Calls by type
        report.append("CALLS BY TYPE")
        report.append("-" * 60)
        calls_by_type = self.get_calls_by_type()
        for call_type, count in sorted(calls_by_type.items()):
            report.append(f"{call_type.capitalize()}: {count}")
        report.append("")
        
        # Duration statistics
        total_duration = self.get_total_duration()
        avg_duration = self.get_average_call_duration()
        report.append("VOICE CALL STATISTICS")
        report.append("-" * 60)
        report.append(f"Total Duration: {total_duration} seconds "
                     f"({total_duration // 60} minutes)")
        report.append(f"Average Duration: {avg_duration:.2f} seconds")
        report.append("")
        
        # Top callers
        report.append("TOP 10 CALLERS")
        report.append("-" * 60)
        top_callers = self.get_top_callers(10)
        for i, (caller, count) in enumerate(top_callers, 1):
            report.append(f"{i}. {caller}: {count} calls")
        report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def main():
    """Main entry point for the CDR Analyzer"""
    if len(sys.argv) < 2:
        print("Usage: python cdr_analyzer.py <cdr_file.csv>")
        print("\nExample:")
        print("  python cdr_analyzer.py sample_cdr.csv")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    # Create analyzer and load data
    analyzer = CDRAnalyzer()
    analyzer.load_from_csv(filename)
    
    # Generate and print report
    report = analyzer.generate_report()
    print("\n" + report)


if __name__ == "__main__":
    main()
