import os
import json
import time
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_test.combined_resolver import BPUTResolver
from api_test.extract_sessions import extract_sessions
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
resolver = BPUTResolver()

EXPORTS_DIR = os.path.abspath("exports")
if not os.path.exists(EXPORTS_DIR):
    os.makedirs(EXPORTS_DIR)

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "timestamp": time.time()}), 200

# Global session cache to avoid redundant fetching
SESSIONS_CACHE = []

def get_cached_sessions():
    global SESSIONS_CACHE
    if not SESSIONS_CACHE:
        SESSIONS_CACHE = extract_sessions()
    return SESSIONS_CACHE

def fetch_student_with_retry(roll_no, session, retries=3):
    """Wrapper for resolver.resolve_all with retry logic."""
    for i in range(retries):
        try:
            result = resolver.resolve_all(roll_no, session)
            # If we got student info or results, consider it a success for that student
            # even if there were some errors in specific semesters (partial success)
            if result.get('student_info') or result.get('available_results'):
                return result
        except Exception as e:
            logger.error(f"Attempt {i+1} failed for {roll_no}: {str(e)}")
            if i == retries - 1:
                return {"roll_no": roll_no, "errors": [{"step": "retry_exhausted", "message": str(e)}]}
        time.sleep(1) # Small delay between retries
    return {"roll_no": roll_no, "errors": [{"step": "failed", "message": "Max retries reached"}]}

@app.route('/')
def index():
    sessions = get_cached_sessions()
    return render_template('index.html', sessions=sessions)

@app.route('/api/sessions')
def api_sessions():
    return jsonify(get_cached_sessions())

@app.route('/api/reports')
def list_reports():
    """Lists all generated Excel reports."""
    files = [f for f in os.listdir(EXPORTS_DIR) if f.endswith('.xlsx')]
    # Return with stats
    reports = []
    for f in files:
        path = os.path.join(EXPORTS_DIR, f)
        reports.append({
            "filename": f,
            "size": os.path.getsize(path),
            "created": os.path.getctime(path)
        })
    # Sort by creation time (newest first)
    reports.sort(key=lambda x: x['created'], reverse=True)
    return jsonify(reports)

@app.route('/download/<filename>')
def download_report(filename):
    return send_from_directory(EXPORTS_DIR, filename, as_attachment=True)

@app.route('/stream-results')
def stream_results():
    start_reg = request.args.get('start_reg')
    end_reg = request.args.get('end_reg')
    session = request.args.get('session')
    threads = int(request.args.get('threads', 5))
    retries = int(request.args.get('retries', 3))

    if not all([start_reg, end_reg, session]):
        return jsonify({"error": "Missing parameters"}), 400

    try:
        start_val = int(start_reg)
        end_val = int(end_reg)
        roll_numbers = [str(r) for r in range(start_val, end_val + 1)]
    except ValueError:
        return jsonify({"error": "Invalid registration range"}), 400

    def generate():
        all_results = []
        
        # 1. Pre-fetch the first student to get common header info (sequential)
        first_roll = roll_numbers[0]
        logger.info(f"Pre-fetching header info from {first_roll}")
        first_data = fetch_student_with_retry(first_roll, session, retries)
        
        if first_data.get('student_info'):
            info = first_data['student_info']
            available = first_data.get('available_results', [])
            sem_text = available[0].get('semester', 'N/A') if available else 'N/A'
            
            header_data = {
                "type": "header",
                "college": info.get('collegeName', 'N/A'),
                "branch": info.get('branchName', 'N/A'),
                "course": info.get('courseName', 'N/A'),
                "session": session,
                "semester": sem_text
            }
            yield f"data: {json.dumps(header_data)}\n\n"
        
        # Add first_data to all_results so we don't fetch it again or at least we have it
        all_results.append(first_data)
        yield f"data: {json.dumps({'type': 'student', 'data': first_data})}\n\n"

        # 2. Process the rest in parallel
        remaining_rolls = roll_numbers[1:]
        if remaining_rolls:
            with ThreadPoolExecutor(max_workers=threads) as executor:
                future_to_roll = {executor.submit(fetch_student_with_retry, roll, session, retries): roll for roll in remaining_rolls}
                
                for future in as_completed(future_to_roll):
                    data = future.result()
                    
                    all_results.append(data)
                    yield f"data: {json.dumps({'type': 'student', 'data': data})}\n\n"

        # 3. Generate Excel
        if all_results:
            excel_filename = generate_excel_report(all_results, session)
            yield f"data: {json.dumps({'type': 'complete', 'report_url': f'/download/{excel_filename}'})}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Transfer-Encoding': 'chunked',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    })

def generate_excel_report(results, session):
    """Generates a professional Excel report from the results."""
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
        return "error_no_data.xlsx"

    df = pd.DataFrame(rows)
    
    first_res = next((r for r in results if r.get('student_info')), None)
    if first_res:
        info = first_res['student_info']
        college = info.get('collegeCode', 'BPUT')
        course = info.get('courseName', 'Course').replace('.', '').replace(' ', '')
        branch = info.get('branchName', 'Branch').split('(')[-1].replace(')', '').replace(' ', '')[:5]
        sem = "Report"
        if first_res.get('detailed_results'):
            first_sem_key = list(first_res['detailed_results'].keys())[0]
            sem_data = first_res['detailed_results'][first_sem_key]
            if sem_data.get('grades'):
                sem = sem_data['grades'][0].get('semester', 'Sem').replace(' ', '')

        filename = f"{college}_{course}_{branch}_{sem}_{int(time.time())}.xlsx"
    else:
        filename = f"BPUT_Report_{int(time.time())}.xlsx"

    save_path = os.path.join(EXPORTS_DIR, filename)
    df.to_excel(save_path, index=False)
    return filename

if __name__ == '__main__':
    # For Render/Cloud deployment
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
