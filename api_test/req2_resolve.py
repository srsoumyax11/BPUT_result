import requests

def resolve_grades(roll_no, session, sem_id):
    """
    REQ 2: Fetches detailed subject-wise grades and SGPA.
    Returns: Dict with grades list and sgpa details.
    """
    url = "https://results.bput.ac.in/student-results-subjects-list"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Content-Type": "application/json; charset=utf-8",
        "X-Requested-With": "XMLHttpRequest"
    }
    params = {
        "semid": str(sem_id),
        "rollNo": str(roll_no),
        "session": session
    }

    try:
        response = requests.post(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "grades": data.get("grades", []),
                "sgpa": data.get("sgpadetails", {}).get("sgpa", "N/A"),
                "total_credits": data.get("sgpadetails", {}).get("cretits", "N/A")
            }
    except Exception as e:
        return {"error": str(e)}
    return None

if __name__ == "__main__":
    test_roll = "2301230101"
    test_session = "Odd-(2025-26)"
    test_sem_id = "5"
    result = resolve_grades(test_roll, test_session, test_sem_id)
    print(f"--- Grades for {test_roll} (SemID: {test_sem_id}) ---")
    print(f"SGPA: {result['sgpa']}")
    for g in result['grades']:
        print(f"[{g.get('subjectCODE')}] {g.get('subjectName')}: {g.get('grade')}")
