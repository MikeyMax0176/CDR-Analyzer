# CDR-Analyzer
Analyze Call Detail Records

## Overview
CDR-Analyzer is a Python program for analyzing Call Detail Records (CDR). It can parse CDR data from CSV files and generate comprehensive reports including call statistics, durations, costs, and top callers.

## Features
- Load and parse CDR data from CSV files
- Calculate total calls, duration, and costs
- Analyze calls by type (voice, SMS, data)
- Identify top callers
- Generate detailed analysis reports

## Installation
No external dependencies required. The program uses Python's standard library only.

```bash
# Clone the repository
git clone https://github.com/MikeyMax0176/CDR-Analyzer.git
cd CDR-Analyzer
```

## Usage

### Basic Usage
```bash
python cdr_analyzer.py <cdr_file.csv>
```

### Example
```bash
python cdr_analyzer.py sample_cdr.csv
```

### CSV File Format
The CDR CSV file should have the following columns:
- `caller`: Phone number of the caller
- `recipient`: Phone number of the recipient
- `type`: Call type (voice, sms, data)
- `duration`: Duration in seconds (for voice) or bytes (for data)
- `timestamp`: Timestamp of the call
- `cost`: Cost of the call in dollars

Example:
```csv
caller,recipient,type,duration,timestamp,cost
+1234567890,+1987654321,voice,120,2024-01-15 09:30:00,0.50
+1234567890,+1555123456,sms,0,2024-01-15 09:35:00,0.10
```

## Sample Data
A sample CDR file (`sample_cdr.csv`) is included in the repository for testing purposes.

## Running Tests
```bash
python test_cdr_analyzer.py
```

## Output
The analyzer generates a report including:
- Total number of records
- Total cost
- Calls by type (voice, SMS, data)
- Voice call statistics (total duration, average duration)
- Top 10 callers by number of calls

## License
MIT License
