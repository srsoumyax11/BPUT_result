import requests

def resolve_result_list(roll_no, session, dob="2005-06-18"):
    """
    REQ 1: Fetches available results for a student and session.
    Returns: List of available semesters/exams.
    """
    url = "https://results.bput.ac.in/student-results-list"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Content-Type": "application/json; charset=utf-8",
        "X-Requested-With": "XMLHttpRequest"
    }
    params = {
        "rollNo": str(roll_no),
        "dob": dob,
        "session": session
    }

    try:
        response = requests.post(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json() # Returns list of result objects
    except Exception as e:
        return {"error": str(e)}
    return []

if __name__ == "__main__":
    test_roll = "2301230101"
    test_session = "Odd-(2025-26)"
    result = resolve_result_list(test_roll, test_session)
    print(f"--- Available Results for {test_roll} in {test_session} ---")
    for r in result:
        print(f"Semester: {r.get('semester')} | SemID: {r.get('semId')}")
