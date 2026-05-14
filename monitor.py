import os
import json
import time
from api_test.extract_sessions import extract_sessions
from scraper import fetch_student_with_retry, generate_excel, generate_pdf
from concurrent.futures import ThreadPoolExecutor, as_completed

# Config (Override these in GitHub Actions Secrets/Variables)
START_ROLL = int(os.getenv("START_ROLL", 2301230001))
END_ROLL = int(os.getenv("END_ROLL", 2301230020)) # Default small range
THREADS = int(os.getenv("THREADS", 10))
RETRIES = 3

def run_scraper(session_value):
    rolls = [str(r) for r in range(START_ROLL, END_ROLL + 1)]
    all_results = []
    
    print(f"\n[BOT] Starting Batch Extraction...")
    print(f"[BOT] Session: {session_value}")
    print(f"[BOT] Range:   {START_ROLL} to {END_ROLL}")
    
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(fetch_student_with_retry, roll, session_value, RETRIES): roll for roll in rolls}
        
        done = 0
        for future in as_completed(futures):
            res = future.result()
            all_results.append(res)
            done += 1
            status = "OK" if res.get('detailed_results') else "EMPTY"
            print(f"[{done}/{len(rolls)}] {res['roll_no']} - {status}")

    # Generate Reports
    excel_path = generate_excel(all_results)
    pdf_paths = generate_pdf(all_results)
    
    print(f"\n[BOT] SUCCESS!")
    print(f"[BOT] Excel: {excel_path}")
    print(f"[BOT] PDFs:  {len(pdf_paths)} files generated.")
    return excel_path, pdf_paths

def main():
    print("=== BPUT AUTOMATED MONITOR ===")
    
    available_sessions = extract_sessions()
    if not available_sessions:
        print("[ERROR] Could not fetch available sessions.")
        return

    # Usually the first one in the dropdown is the latest
    latest_session = available_sessions[0]
    latest_val = latest_session['value']
    latest_text = latest_session['text']

    # Check for state
    state_file = "api_test/last_session.txt"
    last_val = ""
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            last_val = f.read().strip()

    print(f"[INFO] Latest on Portal: {latest_text} ({latest_val})")
    print(f"[INFO] Last Processed:   {last_val if last_val else 'NONE'}")

    if latest_val != last_val:
        print(f"\n[ALERT] NEW SESSION DETECTED! Triggering automation...")
        try:
            run_scraper(latest_val)
            
            # Save state only if successful
            with open(state_file, "w") as f:
                f.write(latest_val)
            print(f"[INFO] State updated to {latest_val}")
            
        except Exception as e:
            print(f"[ERROR] Automation failed: {str(e)}")
    else:
        print("[INFO] No new sessions. Standing by.")

if __name__ == "__main__":
    main()
