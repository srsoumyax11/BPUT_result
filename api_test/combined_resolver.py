import requests
import json
import logging

# Configure logging for better debuggability
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class BPUTResolver:
    """
    Combined resolver for BPUT results API.
    Returns ALL raw fields from all three API endpoints.
    """
    
    BASE_URL = "https://results.bput.ac.in"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Content-Type": "application/json; charset=utf-8",
        "X-Requested-With": "XMLHttpRequest"
    }

    def __init__(self, timeout=10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _post_request(self, endpoint, params, description):
        """Helper to handle POST requests with error reporting."""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = self.session.post(url, params=params, timeout=self.timeout)
            
            if response.status_code != 200:
                error_msg = f"Failed {description}: HTTP {response.status_code} - {response.reason}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg, "status_code": response.status_code}
            
            try:
                return {"success": True, "data": response.json()}
            except json.JSONDecodeError:
                error_msg = f"Failed {description}: Invalid JSON response from server."
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

        except requests.exceptions.Timeout:
            error_msg = f"Failed {description}: Request timed out after {self.timeout}s."
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed {description}: Network error - {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_student_info(self, roll_no):
        """
        REQ 3: Fetches basic student profile details (Full Data).
        """
        params = {"rollNo": str(roll_no)}
        res = self._post_request("student-detsils-results", params, f"fetching student info for {roll_no}")
        
        if res["success"]:
            return {"success": True, "data": res["data"]}
        return res

    def get_result_list(self, roll_no, session, dob="2005-06-18"):
        """
        REQ 1: Fetches available results list (Full Data).
        """
        params = {
            "rollNo": str(roll_no),
            "dob": dob,
            "session": session
        }
        res = self._post_request("student-results-list", params, f"fetching result list for {roll_no} in {session}")
        
        if res["success"]:
            return {"success": True, "results": res["data"]}
        return res

    def get_grades(self, roll_no, session, sem_id):
        """
        REQ 2: Fetches detailed subject-wise grades and SGPA (Full Data).
        """
        params = {
            "semid": str(sem_id),
            "rollNo": str(roll_no),
            "session": session
        }
        res = self._post_request("student-results-subjects-list", params, f"fetching grades for {roll_no} (SemID: {sem_id})")
        
        if res["success"]:
            return {"success": True, "data": res["data"]}
        return res

    def resolve_all(self, roll_no, session, dob="2005-06-18"):
        """
        Combines all three requests to return a complete student profile with results.
        Returns ALL fields provided by the BPUT API in a single object.
        """
        response = {
            "roll_no": roll_no,
            "session": session,
            "student_info": None,
            "available_results": [],
            "detailed_results": {}, # Maps semId -> Full API response
            "errors": []
        }

        # 1. Get Student Info
        info = self.get_student_info(roll_no)
        if info["success"]:
            response["student_info"] = info["data"]
        else:
            response["errors"].append({"step": "student_info", "message": info.get("error")})

        # 2. Get Available Results
        results_list = self.get_result_list(roll_no, session, dob)
        if results_list["success"]:
            response["available_results"] = results_list["results"]
            
            # 3. Get Full Details for each available semId
            for res_item in results_list["results"]:
                sem_id = res_item.get("semId")
                if sem_id:
                    grades_data = self.get_grades(roll_no, session, sem_id)
                    if grades_data["success"]:
                        response["detailed_results"][sem_id] = grades_data["data"]
                    else:
                        response["errors"].append({
                            "step": f"grades_sem_{sem_id}", 
                            "message": grades_data.get("error")
                        })
        else:
            response["errors"].append({"step": "result_list", "message": results_list.get("error")})

        return response

if __name__ == "__main__":
    resolver = BPUTResolver()
    
    test_roll = input("Test Reg: ")
    test_session = input('Ex: "Odd-(2025-26)"')
    
    print(f"--- Resolving all data for {test_roll} ---")
    full_data = resolver.resolve_all(test_roll, test_session)
    
    # OUTPUT EVERYTHING COMBINED INTO ONE JSON
    print(json.dumps(full_data, indent=4))
    
    if full_data["errors"]:
        print("\n--- Errors encountered ---")
        for err in full_data["errors"]:
            print(f"[{err['step']}] {err['message']}")
