import requests

def resolve_student_info(roll_no):
    """
    REQ 3: Fetches basic student profile details.
    Returns: Dict with Name, College, Branch, etc.
    """
    url = "https://results.bput.ac.in/student-detsils-results"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Content-Type": "application/json; charset=utf-8",
        "X-Requested-With": "XMLHttpRequest"
    }
    params = {"rollNo": str(roll_no)}

    try:
        response = requests.post(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "name": data.get("studentName"),
                "college": data.get("collegeName"),
                "branch": data.get("branchName"),
                "course": data.get("courseName")
            }
    except Exception as e:
        return {"error": str(e)}
    return None

if __name__ == "__main__":
    # Test for a single student
    test_roll = "2301230101"
    result = resolve_student_info(test_roll)
    print(f"--- Student Info for {test_roll} ---")
    print(result)
