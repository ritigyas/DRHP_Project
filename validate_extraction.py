import os
import sys

# Ensure the backend directory is in the import path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.classifier import DocumentClassifier
from app.parser import DocumentParser
from app.verifier import DocumentVerifier

def main():
    print("=" * 70)
    print("   DRHP CAPITAL STRUCTURE DRAFTING AGENT - VERIFICATION SUITE")
    print("=" * 70)

    dataset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "dataset"))
    if not os.path.exists(dataset_dir):
        print(f"Error: Dataset directory not found at {dataset_dir}")
        sys.exit(1)

    print(f"Scanning synthetic dataset under: {dataset_dir}\n")

    # Ingest and classify all files
    processed_data = {}
    for root, _, files in os.walk(dataset_dir):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content_str = f.read()
                    
                    classification = DocumentClassifier.classify(content_str, file)
                    doc_type = classification["document_type"]
                    parsed_data = DocumentParser.parse_document(doc_type, content_str)
                    
                    processed_data[file] = {
                        "content": content_str,
                        "filename": file,
                        "classification": classification,
                        "parsed_data": parsed_data
                    }
                except Exception as e:
                    print(f"Error processing file {file}: {e}")

    # Group by event_id
    grouped_events = {}
    for filename, file_info in processed_data.items():
        event_id = file_info["classification"]["event_id"]
        doc_type = file_info["classification"]["document_type"]
        if event_id == "UNKNOWN" or doc_type == "UNKNOWN":
            continue
        
        if event_id not in grouped_events:
            grouped_events[event_id] = {}
        
        grouped_events[event_id][doc_type] = file_info

    # Run verifier for each event
    print("-" * 70)
    print("Running cross-reference verifications:")
    print("-" * 70)
    
    events_results = []
    for event_id in sorted(grouped_events.keys()):
        event_docs = grouped_events[event_id]
        result = DocumentVerifier.verify_event(event_id, event_docs)
        events_results.append(result)

        print(f"\n[EVENT] {result['title']}")
        print(f"  Filing Date: {result['sh7_filing_date']}")
        print(f"  Resolution Date: {result['egm_date']} ({result.get('meeting_type', 'EGM')})")
        print(f"  Pre-capital:  Rs. {result['total_capital_before']:,}")
        print(f"  Post-capital: Rs. {result['total_capital_after']:,}")
        
        status_color = "\033[92mConfirmed\033[0m" if result['status'] == 'Confirmed' else "\033[93mFlagged\033[0m"
        # Standard fallback if terminal color codes aren't supported
        print(f"  Status: {result['status']}")
        
        print("  Checks Log:")
        for log in result['verification_logs']:
            icon = "✓" if log['status'] == 'PASS' else "⚠" if log['status'] == 'WARN' else "✗"
            print(f"    [{icon}] {log['label']}: {log['message']}")
            
        if result['anomalies']:
            print("  Anomalies Block:")
            for anom in result['anomalies']:
                print(f"    - {anom}")
                
    print("\n" + "=" * 70)
    print("   ASSERTION VALIDATIONS")
    print("=" * 70)

    # Convert results list to dictionary for assertions
    results_map = {r['event_id']: r for r in events_results}

    # Assert Event 1 is fully Confirmed
    assert 'Event1' in results_map, "Event1 missing"
    assert results_map['Event1']['status'] == 'Confirmed', "Assertion Failed: Event 1 should be 'Confirmed'."
    print("✓ Assertion Passed: Event 1 is fully Confirmed.")

    # Assert Event 2 is Flagged
    assert 'Event2' in results_map, "Event2 missing"
    assert results_map['Event2']['status'] == 'Flagged', "Assertion Failed: Event 2 should be 'Flagged'."
    assert any("MOA" in anom for anom in results_map['Event2']['anomalies']), "Assertion Failed: Event 2 should have a MOA clause anomaly."
    print("✓ Assertion Passed: Event 2 is Flagged with MOA mismatch details.")

    # Assert Event 3 is Flagged
    assert 'Event3' in results_map, "Event3 missing"
    assert results_map['Event3']['status'] == 'Flagged', "Assertion Failed: Event 3 should be 'Flagged'."
    assert any("Draft" in anom for anom in results_map['Event3']['anomalies']), "Assertion Failed: Event 3 should have a Draft document anomaly."
    assert any("EGM Date mismatch" in anom or "date" in anom.lower() for anom in results_map['Event3']['anomalies']), "Assertion Failed: Event 3 should have a date mismatch anomaly."
    print("✓ Assertion Passed: Event 3 is Flagged with unsigned draft and meeting date mismatch.")

    print("\n" + "=" * 70)
    print("   ALL AUTOMATED VERIFICATION CHECKS PASSED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    main()
