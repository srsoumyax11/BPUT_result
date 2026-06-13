import requests
import json

def test_request():
    url = "https://results.bput.ac.in/student-results-list"
    params = {
        "rollNo": "2301110123",
        "dob": "2020-01-28",
        "session": "Odd-(2025-26)"
    }
    
    headers = {
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
        "Priority": "u=1, i"
    }

    print(f"Testing Request 1: {url}")
    try:
        response = requests.post(url, params=params, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        result = {
            "status_code": response.status_code,
            "url": response.url,
            "response": response.text
        }
        
        try:
            result["response_json"] = response.json()
        except:
            result["response_json"] = None
            
        with open("api_test/result_req1.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print("Result saved to api_test/result_req1.json")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_request()
