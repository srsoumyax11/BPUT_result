import requests
import time

class StudentNotFoundError(Exception):
    """Raised when a student registration number is not found on the portal."""
    pass

class BPUTScraper:
    def __init__(self, fixed_dob="2005-06-18"):
        self.fixed_dob = fixed_dob
        self.headers = {
            "Host": "results.bput.ac.in",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Not)A;Brand";v="8", "Chromium";v="138"',
            "Sec-Ch-Ua-Mobile": "?0",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Content-Type": "application/json; charset=utf-8",
            "Origin": "https://results.bput.ac.in",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://results.bput.ac.in/",
            "Accept-Encoding": "gzip, deflate, br",
            "Priority": "u=1, i"
        }

    def fetch_student_info(self, roll_no):
        """Step 1: Get basic student profile."""
        url = "https://results.bput.ac.in/student-detsils-results"
        params = {"rollNo": str(roll_no)}
        try:
            print(f"  [>] Fetching Student Info for {roll_no}...")
            resp = requests.post(url, params=params, headers=self.headers, timeout=12)
            
            if resp.status_code == 404:
                raise StudentNotFoundError(f"Roll No {roll_no} not found.")
            
            if resp.status_code != 200:
                print(f"  [!] Server error: {resp.status_code}")
                return None
                
            data = resp.json()
            # BPUT often returns an empty object or missing name for invalid students even with 200 OK
            if not data or not data.get('studentName'):
                raise StudentNotFoundError(f"Student {roll_no} profile is empty or invalid.")
                
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"  [!] Network Error {roll_no}: {e}")
            return None
        except StudentNotFoundError:
            raise
        except Exception as e:
            print(f"  [!] Unexpected Error {roll_no}: {e}")
            return None

    def fetch_result_list(self, roll_no, session):
        """Step 2: Get list of available result sessions."""
        url = "https://results.bput.ac.in/student-results-list"
        params = {
            "rollNo": str(roll_no),
            "dob": self.fixed_dob,
            "session": session
        }
        try:
            print(f"  [>] Searching for Session Result...")
            resp = requests.post(url, params=params, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"  [!] Error Sessions {roll_no}: {e}")
        return None

    def fetch_grades(self, roll_no, session, sem_id):
        """Step 3: Get detailed grades for a specific semester."""
        url = "https://results.bput.ac.in/student-results-subjects-list"
        params = {
            "semid": str(sem_id),
            "rollNo": str(roll_no),
            "session": session
        }
        try:
            print(f"  [>] Pulling Detailed Grades (SemID: {sem_id})...")
            resp = requests.post(url, params=params, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"  [!] Error Grades {roll_no}: {e}")
        return None

    def get_full_result(self, roll_no, session):
        """Orchestrate the fetching process for ALL semesters in the session."""
        all_results = []
        try:
            print(f"\n" + "-"*40)
            print(f"ROLL: {roll_no} | SESSION: {session}")
            print("-"*40)
            
            # 1. Student Info
            info = self.fetch_student_info(roll_no)
                
            # 2. Result List
            res_list = self.fetch_result_list(roll_no, session)
            if not res_list:
                print(f"  [x] No result session found for {session}.")
                return [{
                    "Roll No": str(roll_no),
                    "Name": info.get('studentName', 'Unknown'),
                    "Semester": "Unknown",
                    "SGPA": "N/A", 
                    "Status": "Session Missing",
                    "grades": []
                }]
                
            # 3. Grades for each Semester
            for res_item in res_list:
                sem_name = res_item.get('semester', 'N/A')
                sem_id = res_item.get('semId')
                
                print(f"  [>] Processing Semester: {sem_name}")
                grades_data = self.fetch_grades(roll_no, session, sem_id)
                
                grades_list = []
                sgpa = "N/A"
                if grades_data:
                    if 'sgpadetails' in grades_data:
                        sgpa = grades_data['sgpadetails'].get('sgpa', "N/A")
                    grades_list = grades_data.get('grades', [])
                    print(f"    [OK] Found {len(grades_list)} subjects | SGPA: {sgpa}")
                
                all_results.append({
                    "Roll No": str(roll_no),
                    "Name": info.get('studentName'),
                    "Semester": sem_name,
                    "SGPA": sgpa,
                    "Status": "Success" if sgpa != "N/A" else "Partial Success",
                    "grades": grades_list
                })

            return all_results

        except StudentNotFoundError as e:
            print(f"  [x] Not Found: {e}")
            return [{
                "Roll No": str(roll_no),
                "Name": "NOT FOUND",
                "Semester": "N/A",
                "SGPA": "N/A",
                "Status": "Removed/Invalid",
                "grades": []
            }]
        except Exception as e:
            print(f"  [!] Execution Error for {roll_no}: {e}")
            return None
