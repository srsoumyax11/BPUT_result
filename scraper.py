import os
import json
import time
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_test.combined_resolver import BPUTResolver

def fetch_student_with_retry(roll, session, retries=3):
    resolver = BPUTResolver()
    for i in range(retries):
        try:
            return resolver.resolve_all(roll, session)
        except Exception as e:
            if i == retries - 1:
                return {"roll_no": roll, "errors": [{"message": str(e)}], "student_info": {}}
            time.sleep(1)

def generate_excel(results):
    # Sort results by roll number numerically
    results = sorted(results, key=lambda x: int(x.get('roll_no', 0)))
    
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

def generate_pdf(results):
    from fpdf import FPDF
    
    # Sort results by roll number numerically
    results = sorted(results, key=lambda x: int(x.get('roll_no', 0)))
    
    # Group results by Branch and Semester
    groups = {}
    all_sgpas = []
    passed = 0
    total_students = len(results)
    
    for res in results:
        info = res.get('student_info', {})
        branch = info.get('branchName', 'Branch').split('(')[-1].replace(')', '').strip()
        for sem_id, detail in res.get('detailed_results', {}).items():
            sem_name = detail.get('grades', [{}])[0].get('semester', sem_id)
            group_key = f"{branch} - {sem_name}"
            if group_key not in groups:
                groups[group_key] = []
            
            sgpa = float(detail.get('sgpadetails', {}).get('sgpa', 0) or 0)
            all_sgpas.append(sgpa)
            if not any(g.get('grade') in ['F', 'M', 'S'] for g in detail.get('grades', [])):
                passed += 1
                
            groups[group_key].append({
                "roll": res['roll_no'],
                "name": info.get('studentName', 'N/A'),
                "sgpa": detail.get('sgpadetails', {}).get('sgpa', 'N/A'),
                "grades": detail.get('grades', [])
            })

    avg_sgpa = sum(all_sgpas)/len(all_sgpas) if all_sgpas else 0
    pass_rate = (passed/total_students)*100 if total_students else 0
    toppers = sorted(results, key=lambda x: float(list(x.get('detailed_results', {}).values())[0].get('sgpadetails', {}).get('sgpa', 0) or 0) if x.get('detailed_results') else 0, reverse=True)[:3]

    os.makedirs("exports", exist_ok=True)
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    
    # SUMMARY PAGE
    pdf.add_page()
    pdf.set_fill_color(240, 244, 255)
    pdf.rect(10, 10, 277, 40, "F")
    
    pdf.set_font("helvetica", "B", 20)
    pdf.set_text_color(99, 102, 241)
    pdf.text(20, 22, "BPUT BATCH ANALYTICS REPORT")
    
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.text(20, 30, f"Total Students: {total_students}  |  Average SGPA: {avg_sgpa:.2f}  |  Pass Rate: {pass_rate:.1f}%")
    pdf.text(20, 36, f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # TOPPERS BOX
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(218, 165, 32)
    pdf.text(180, 22, "OVERALL TOPPERS")
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(50, 50, 50)
    for idx, t in enumerate(toppers):
        t_name = t.get('student_info', {}).get('studentName', 'N/A')
        t_sgpa = list(t.get('detailed_results', {}).values())[0].get('sgpadetails', {}).get('sgpa', '0') if t.get('detailed_results') else '0'
        pdf.text(180, 28 + (idx*5), f"{idx+1}. {t_name[:35]} ({t_sgpa})")
    
    pdf.ln(50)

    for title, students in groups.items():
        # If it's the first group, we might already have the summary on page 1.
        # For simplicity, let's just start every group on a new page.
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 10, f"Group: {title}", ln=True)
        pdf.ln(5)

        # Get unique subjects for this group
        subjects = []
        for s in students:
            for g in s['grades']:
                if g.get('subjectCODE') not in subjects:
                    subjects.append(g.get('subjectCODE'))
        subjects.sort()

        # Table Header
        pdf.set_font("helvetica", "B", 8)
        pdf.set_fill_color(99, 102, 241) # Indigo Accent
        pdf.set_text_color(255, 255, 255) # White text for header
        
        pdf.cell(25, 8, "Roll No", 1, 0, "C", True)
        pdf.cell(50, 8, "Name", 1, 0, "C", True)
        pdf.cell(15, 8, "SGPA", 1, 0, "C", True)
        
        col_width = 180 / max(len(subjects), 1) if subjects else 20
        for sub in subjects:
            pdf.cell(col_width, 8, sub, 1, 0, "C", True)
        pdf.ln()

        # Rows
        pdf.set_text_color(40, 40, 40) # Dark gray text for rows
        pdf.set_font("helvetica", "", 7)
        
        # Determine medals within this group
        group_students = sorted(students, key=lambda x: float(x['sgpa']) if x['sgpa'] != 'N/A' else 0, reverse=True)
        top_sgpas = sorted(list(set(float(s['sgpa']) for s in students if s['sgpa'] != 'N/A')), reverse=True)
        
        for i, s in enumerate(students):
            # Alternating row background
            fill = i % 2 == 0
            pdf.set_fill_color(248, 250, 252) # Very light gray
            
            # Medal check
            medal = ""
            s_sgpa = float(s['sgpa']) if s['sgpa'] != 'N/A' else 0
            if s_sgpa > 0:
                if s_sgpa == top_sgpas[0]: medal = "G "
                elif len(top_sgpas) > 1 and s_sgpa == top_sgpas[1]: medal = "S "
                elif len(top_sgpas) > 2 and s_sgpa == top_sgpas[2]: medal = "B "
            
            pdf.cell(25, 7, medal + str(s['roll']), 1, 0, "L", fill)
            pdf.cell(50, 7, s['name'][:30], 1, 0, "L", fill)
            
            # SGPA highlighting
            sgpa_val = float(s['sgpa']) if s['sgpa'] != "N/A" else 0
            if sgpa_val >= 8.5: pdf.set_text_color(5, 150, 105) # Green
            elif sgpa_val < 6.0: pdf.set_text_color(220, 38, 38) # Red
            else: pdf.set_text_color(99, 102, 241) # Indigo
            
            pdf.set_font("helvetica", "B", 7)
            pdf.cell(15, 7, str(s['sgpa']), 1, 0, "C", fill)
            pdf.set_font("helvetica", "", 7)
            pdf.set_text_color(40, 40, 40) # Reset text color

            for sub in subjects:
                g = next((x for x in s['grades'] if x.get('subjectCODE') == sub), None)
                grade = g['grade'] if g else "-"
                
                # Highlight fails
                if grade == 'F': pdf.set_text_color(220, 38, 38)
                elif grade in ['S','O','E']: pdf.set_text_color(5, 150, 105)
                
                pdf.cell(col_width, 7, grade, 1, 0, "C", fill)
                pdf.set_text_color(40, 40, 40) # Reset
            pdf.ln()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = title.replace(" ", "_").replace("&", "and")
        pdf_filename = f"{safe_title}_{timestamp}.pdf"
        pdf_path = os.path.join("exports", pdf_filename)
        pdf.output(pdf_path)
        pdf_paths.append(pdf_path)
    
    return pdf_paths

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
