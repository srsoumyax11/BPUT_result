"""
cli/fetcher.py — Multi-threaded fetch engine with retry and timeout escalation.
Uses BPUTResolver from api_test/ to query BPUT endpoints.
Results are collected into a thread-safe sorted buffer.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# We import BPUTResolver using a relative-to-project path.
# This works when running from the project root: python -m cli.main
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_test.combined_resolver import BPUTResolver


# Timeout escalation sequence (seconds) for retries
TIMEOUT_SEQUENCE = [10, 20, 30]


def fetch_single_student(resolver, roll_no, session):
    """
    Fetch a single student's profile + first-semester grades.
    Uses escalating timeouts on retry.

    Returns a dict:
    {
        "roll_no": str,
        "session": str,
        "student_info": dict or None,
        "semester": str,
        "grades_data": dict or None,  # {grades: [...], sgpadetails: {...}}
        "status": "SUCCESS" | "NO_PROFILE" | "NO_RESULTS" | "TIMEOUT" | "ERROR",
        "error": str or None,
    }
    """
    result = {
        "roll_no": str(roll_no),
        "session": session,
        "student_info": None,
        "semester": "N/A",
        "grades_data": None,
        "status": "ERROR",
        "error": None,
    }

    for attempt, timeout in enumerate(TIMEOUT_SEQUENCE):
        try:
            # Create a fresh resolver with this attempt's timeout
            r = BPUTResolver(timeout=timeout)

            # 1. Get student info
            info_res = r.get_student_info(roll_no)
            if not info_res.get("success") or not info_res.get("data"):
                result["status"] = "NO_PROFILE"
                result["error"] = info_res.get("error", "No profile data returned")
                # Don't retry for missing profiles — they genuinely don't exist
                return result

            # Strip massive base64 images to prevent OOM crashes
            student_data = info_res["data"]
            for key in ["studentPic", "studentSign"]:
                student_data.pop(key, None)

            result["student_info"] = student_data

            # 2. Get result list
            list_res = r.get_result_list(roll_no, session)
            if not list_res.get("success") or not list_res.get("results"):
                result["status"] = "NO_RESULTS"
                result["error"] = list_res.get("error", "No results declared for this session")
                return result

            results_list = list_res["results"]
            if not results_list:
                result["status"] = "NO_RESULTS"
                result["error"] = "Empty results list"
                return result

            # Fetch the most recent semester (last in the list)
            first_sem = results_list[-1]
            sem_id = first_sem.get("semId")
            result["semester"] = first_sem.get("semester", f"Sem {sem_id}")

            # 3. Get grades for that semester
            grades_res = r.get_grades(roll_no, session, sem_id)
            if not grades_res.get("success") or not grades_res.get("data"):
                result["status"] = "ERROR"
                result["error"] = grades_res.get("error", "Failed to fetch grades")
                # This could be a timeout — allow retry
                if attempt < len(TIMEOUT_SEQUENCE) - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return result

            result["grades_data"] = grades_res["data"]
            result["status"] = "SUCCESS"
            result["error"] = None
            return result

        except Exception as e:
            error_msg = str(e)
            result["error"] = error_msg

            # Check if it's a timeout/connection error worth retrying
            if any(kw in error_msg.lower() for kw in ["timeout", "connection", "reset", "refused"]):
                result["status"] = "TIMEOUT"
                if attempt < len(TIMEOUT_SEQUENCE) - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            else:
                result["status"] = "ERROR"

            return result

    return result


def fetch_batch(resolver, roll_numbers, session, threads, on_result):
    """
    Fetch a batch of students using ThreadPoolExecutor.

    Args:
        resolver: BPUTResolver instance (used only for its config; each thread
                  creates its own resolver with appropriate timeout)
        roll_numbers: list of roll number strings
        session: session string
        threads: max workers
        on_result: callback(result_dict) called when each student completes.
                   Called from worker threads — must be thread-safe.

    Returns:
        (all_results, failed_results) — both lists of result dicts, sorted by roll_no.
    """
    all_results = {}
    failed_results = []
    lock = threading.Lock()

    def _worker(roll_no):
        result = fetch_single_student(resolver, roll_no, session)
        with lock:
            all_results[roll_no] = result
            if result["status"] not in ("SUCCESS", "NO_PROFILE", "NO_RESULTS"):
                failed_results.append(result)
        # Notify the caller
        if on_result:
            on_result(result)
        return result

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(_worker, roll): roll for roll in roll_numbers}
        for future in as_completed(futures):
            # Exceptions are already handled inside _worker,
            # but catch any unexpected ones here
            try:
                future.result()
            except Exception:
                pass

    # Sort by roll number
    sorted_results = [all_results[r] for r in sorted(all_results.keys())]
    failed_sorted = sorted(failed_results, key=lambda x: x["roll_no"])

    return sorted_results, failed_sorted


def retry_failed(failed_list, session, on_result):
    """
    Retry fetching students that previously failed.
    Uses max timeout (30s) for all retries.

    Returns:
        (retried_results, still_failed) — both sorted by roll_no.
    """
    retried = []
    still_failed = []

    resolver = BPUTResolver(timeout=30)

    for item in failed_list:
        roll_no = item["roll_no"]
        result = fetch_single_student(resolver, roll_no, session)
        retried.append(result)
        if result["status"] not in ("SUCCESS", "NO_PROFILE", "NO_RESULTS"):
            still_failed.append(result)
        if on_result:
            on_result(result)

    retried.sort(key=lambda x: x["roll_no"])
    still_failed.sort(key=lambda x: x["roll_no"])
    return retried, still_failed
