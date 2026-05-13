import os
import json
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_test.combined_resolver import BPUTResolver

def fetch_student_with_retry(roll, session, retries=3):
    resolver = BPUTResolver()
    return resolver.resolve_all(roll, session, max_retries=retries)

def generate_excel(results):
    rows = []
    all_subject_codes = set()
    
    for res in results:
        for sem_id, detail in res.get('detailed_results', {}).items():
            for g in detail.get('grades', []):
                code = g.get('subjectCODE')
                if code:
                    all_subject_codes.add(code)
    
    sorted_subjects = sorted(list(all_subject_codes))
    
    for res in results:
        info = res.get('student_info', {})
        roll = res.get('roll_no')
        name = info.get('studentName', 'N/A')
        
        for sem_id, detail in res.get('detailed_results', {}).items():
            row = {
                "Roll No": roll,
                "Name": name,
                "Semester": detail.get('grades', [{}])[0].get('semester', sem_id),
                "SGPA": detail.get('sgpadetails', {}).get('sgpa', 'N/A')
            }
            for code in sorted_subjects:
                row[code] = ""
            for g in detail.get('grades', []):
                code = g.get('subjectCODE')
                if code:
                    row[code] = g.get('grade', '')
            rows.append(row)

    if not rows:
        return None

    df = pd.DataFrame(rows)
    
    # Filename generation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"CLI_Report_{timestamp}.xlsx"
    
    first_res = next((r for r in results if r.get('student_info')), None)
    if first_res:
        info = first_res['student_info']
        college = info.get('collegeCode', 'BPUT')
        branch = info.get('branchName', 'Branch').split('(')[-1].replace(')', '').replace(' ', '')[:5]
        filename = f"{college}_{branch}_{timestamp}.xlsx"

    os.makedirs("exports", exist_ok=True)
    filepath = os.path.join("exports", filename)
    df.to_excel(filepath, index=False)
    return filepath

def main():
    print("\n" + "="*40)
    print("      BPUT RESULT SCRAPER (CLI)      ")
    print("="*40)
    
    try:
        start_roll = int(input("Enter Start Registration No: "))
        end_roll = int(input("Enter End Registration No:   "))
        session = input("Enter Session (e.g. Odd-(2025-26)): ")
        threads = input("Number of Threads (default 10): ")
        threads = int(threads) if threads.strip() else 10
        retries = 3
        
        rolls = [str(r) for r in range(start_roll, end_roll + 1)]
        all_results = []
        
        print(f"\n[INFO] Starting extraction for {len(rolls)} students...")
        print(f"[INFO] Using {threads} threads...")
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_roll = {executor.submit(fetch_student_with_retry, roll, session, retries): roll for roll in rolls}
            
            done = 0
            for future in as_completed(future_to_roll):
                data = future.result()
                all_results.append(data)
                done += 1
                
                status = "OK" if data.get('detailed_results') else "NO DATA"
                name = data['student_info'].get('studentName', 'UNKNOWN')
                print(f"[{done}/{len(rolls)}] {data['roll_no']} | {status.ljust(7)} | {name}")

        print("\n[INFO] Extraction complete. Generating Excel...")
        filepath = generate_excel(all_results)
        
        if filepath:
            print(f"[SUCCESS] Report saved to: {os.path.abspath(filepath)}")
        else:
            print("[WARNING] No data found to save.")
            
    except KeyboardInterrupt:
        print("\n[ABORTED] Operation cancelled by user.")
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")

if __name__ == "__main__":
    main()
