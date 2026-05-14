import requests
from bs4 import BeautifulSoup
import json

def extract_sessions():
    url = "https://results.bput.ac.in/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    print(f"Fetching {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Save for analysis
        with open("api_test/portal_home.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Saved home page to api_test/portal_home.html")

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the session dropdown
        # Usually it's a <select> element. Let's find all selects.
        selects = soup.find_all('select')
        
        sessions = []
        for s in selects:
            # Common IDs or names for session dropdowns
            # We'll look for any select that has "session" in its ID/Name or options
            options = s.find_all('option')
            if any("Odd" in opt.text or "Even" in opt.text for opt in options):
                print(f"Found potential session dropdown: ID={s.get('id')}, Name={s.get('name')}")
                for opt in options:
                    val = opt.get('value')
                    text = opt.text.strip()
                    # Exclude placeholders
                    if val and text and val != "0" and "Select" not in text and val != "default_option":
                        sessions.append({"value": val, "text": text})
                break
        
        if not sessions:
            print("Could not find session dropdown using simple heuristics.")
            # Fallback: search for all options with "Odd" or "Even"
            all_options = soup.find_all('option')
            for opt in all_options:
                if "Odd" in opt.text or "Even" in opt.text:
                    sessions.append({"value": opt.get('value'), "text": opt.text.strip()})
        
        return sessions

    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    available_sessions = extract_sessions()
    print("\n--- AVAILABLE SESSIONS ---")
    if available_sessions:
        for s in available_sessions:
            print(f"Text: {s['text']} | Value: {s['value']}")
        
        # Save to JSON for later use
        with open("api_test/sessions.json", "w", encoding="utf-8") as f:
            json.dump(available_sessions, f, indent=2)
        print("\nSessions saved to api_test/sessions.json")
    else:
        print("No sessions found.")
