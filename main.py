import os
import sys
import json
import uuid
import asyncio
import threading
import datetime
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from api_test.combined_resolver import BPUTResolver
from cli.fetcher import fetch_batch
from cli.excel_writer import ExcelWriter

app = FastAPI()

# Ensure exports directory exists
os.makedirs("exports", exist_ok=True)

class SingleFetchRequest(BaseModel):
    rollNo: str
    session: str = "" # Default empty string so it's not required when fetchAll is true
    fetchAll: bool

def generate_sessions_list(roll_no: str):
    if len(roll_no) < 2:
        return []
    try:
        adm_year_short = int(roll_no[:2])
    except ValueError:
        return []
    
    adm_year = 2000 + adm_year_short
    now = datetime.datetime.now()
    current_year = now.year
    current_month = now.month
    
    sessions = []
    for y in range(adm_year, current_year + 1):
        ay_str = f"{y}-{str(y+1)[-2:]}"
        sessions.append(f"Odd-({ay_str})")
        sessions.append(f"Even-({ay_str})")
        
    session_type = "Even" if current_month >= 6 else "Odd"
    current_ay_str = f"{current_year - 1}-{str(current_year)[-2:]}"
    current_session = f"{session_type}-({current_ay_str})"
    
    if current_session in sessions:
        idx = sessions.index(current_session)
        sessions = sessions[:idx+1]
        
    return sessions

@app.post("/api/fetch-single")
async def fetch_single(req: SingleFetchRequest):
    resolver = BPUTResolver()
    
    if req.fetchAll:
        sessions = generate_sessions_list(req.rollNo)
        all_results = []
        student_info = None
        
        for sess in sessions:
            data = resolver.resolve_all(req.rollNo, sess)
            if data.get("student_info"):
                student_info = data["student_info"]
            
            if data.get("detailed_results"):
                for sem_id, sem_data in data.get("detailed_results", {}).items():
                    all_results.append({
                        "semId": sem_id,
                        "semester": sem_data.get("semester", f"Sem {sem_id}"),
                        "examSession": sess,
                        "detailed_grades": sem_data
                    })
                
        return {
            "roll_no": req.rollNo,
            "session": "ALL_SESSIONS",
            "student_info": student_info,
            "results": all_results
        }
    else:
        # Fetch just the specific session provided
        data = resolver.resolve_all(req.rollNo, req.session)
        formatted_results = []
        if data.get("detailed_results"):
            for sem_id, sem_data in data.get("detailed_results", {}).items():
                formatted_results.append({
                    "semId": sem_id,
                    "semester": sem_data.get("semester", f"Sem {sem_id}"),
                    "examSession": req.session,
                    "detailed_grades": sem_data
                })
        return {
            "roll_no": req.rollNo,
            "session": req.session,
            "student_info": data.get("student_info"),
            "results": formatted_results
        }

class BatchFetchRequest(BaseModel):
    startRoll: str
    endRoll: str
    session: str

batch_queues = {}

def run_batch_task(task_id: str, start_roll: int, end_roll: int, session: str, loop, queue: asyncio.Queue):
    try:
        resolver = BPUTResolver(timeout=15)
        excel = ExcelWriter(session)
        
        roll_numbers = [str(r) for r in range(start_roll, end_roll + 1)]
        
        def on_result(result):
            # Send live progress to the frontend via SSE queue
            asyncio.run_coroutine_threadsafe(queue.put({"type": "progress", "data": result}), loop)
            
            # Write successful results to the Excel file
            status = result.get("status")
            if status == "SUCCESS":
                info = result.get("student_info") or {}
                name = info.get("studentName", "N/A")
                branch = info.get("branchName", "UNKNOWN")
                sem = result.get("semester", "N/A")
                grades_data = result.get("grades_data") or {}
                sgpa = grades_data.get("sgpadetails", {}).get("sgpa", "N/A")
                grades_list = grades_data.get("grades", [])
                
                grades_dict = {}
                subject_codes = []
                subject_name_map = {}
                for g in grades_list:
                    code = g.get("subjectCODE")
                    if code:
                        grades_dict[code] = g.get("grade", "—")
                        if code not in subject_codes:
                            subject_codes.append(code)
                        subject_name_map[code] = g.get("subjectName", "Unknown")
                        
                # Handle Excel sections
                # We need to detect if the branch has changed.
                current_branch = getattr(excel, 'current_branch', None)
                
                if not excel.current_subject_codes or current_branch != branch:
                    if excel.current_subject_codes:
                        excel.write_subject_footer() # Close previous section
                    excel.current_branch = branch
                    excel.start_branch_section(branch, sem, subject_codes, subject_name_map)
                else:
                    for code in subject_codes:
                        if code not in excel.current_subject_codes:
                            excel.current_subject_codes.append(code)
                            excel.add_new_subject_header(code, subject_name_map.get(code, "Unknown"))
                
                excel.add_student_row(result["roll_no"], name, sgpa, grades_dict)
                
        # Start the batch fetch (uses a ThreadPool internally)
        fetch_batch(resolver, roll_numbers, session, threads=5, on_result=on_result)
        
        # Save and close excel
        excel.write_subject_footer()
        excel.close()
        
        # Notify frontend that we are done and where the file is
        asyncio.run_coroutine_threadsafe(queue.put({"type": "done", "filename": excel.filename}), loop)
        
    except Exception as e:
        asyncio.run_coroutine_threadsafe(queue.put({"type": "error", "message": str(e)}), loop)


@app.post("/api/start-batch")
async def start_batch(req: BatchFetchRequest):
    task_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    batch_queues[task_id] = queue
    
    loop = asyncio.get_running_loop()
    
    # Run the heavy processing in a background thread to avoid blocking the async event loop
    thread = threading.Thread(
        target=run_batch_task, 
        args=(task_id, int(req.startRoll), int(req.endRoll), req.session, loop, queue)
    )
    thread.start()
    
    return {"task_id": task_id}

@app.get("/api/stream-batch")
async def stream_batch(task_id: str, request: Request):
    queue = batch_queues.get(task_id)
    if not queue:
        return {"error": "Invalid task ID"}
        
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            
            msg = await queue.get()
            yield json.dumps(msg)
            
            if msg["type"] in ["done", "error"]:
                # Clean up queue to prevent memory leaks
                del batch_queues[task_id]
                break
                
    return EventSourceResponse(event_generator())

@app.get("/api/exports")
async def list_exports():
    """Returns a list of all past exported Excel files."""
    files = []
    if os.path.exists("exports"):
        files = [f for f in os.listdir("exports") if f.endswith('.xlsx')]
        files.sort(reverse=True) # Newest first
    return {"files": files}

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Downloads a specific Excel file."""
    filepath = os.path.join("exports", filename)
    if os.path.exists(filepath):
        return FileResponse(
            path=filepath, 
            filename=filename, 
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    return {"error": "File not found"}

# Mount the static frontend HTML/CSS/JS (Must be at the bottom so it doesn't override /api)
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
