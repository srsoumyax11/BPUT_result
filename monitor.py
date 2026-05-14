import os
import time
import requests
from api_test.extract_sessions import extract_sessions

# NTFY Topic (Subscribe to this on your phone/browser)
NTFY_TOPIC = "bput_results_srsoumyax11"

def send_notification(session_text):
    """Sends 2 back-to-back notifications to ntfy.sh."""
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    payload = f"BPUT UPDATE: New Session '{session_text}' is now available on the portal!"
    headers = {
        "Title": "BPUT NEW SESSION DETECTED",
        "Priority": "high",
        "Tags": "loudspeaker,star"
    }
    
    for i in range(2):
        try:
            requests.post(url, data=payload, headers=headers, timeout=10)
            print(f"[BOT] Notification {i+1} sent.")
            if i == 0: time.sleep(2) # Brief gap
        except Exception as e:
            print(f"[ERROR] Failed to send notification: {e}")

def main():
    print("=== BPUT SESSION WATCHER ===")
    
    available_sessions = extract_sessions()
    if not available_sessions:
        print("[ERROR] Could not fetch sessions from portal.")
        return

    # The first one is usually the latest
    latest_session = available_sessions[0]
    latest_val = latest_session['value']
    latest_text = latest_session['text']

    state_file = "api_test/last_session.txt"
    last_val = ""
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            last_val = f.read().strip()

    print(f"[INFO] Portal: {latest_text} ({latest_val})")
    print(f"[INFO] Last:   {last_val if last_val else 'NONE'}")

    if latest_val != last_val:
        print(f"\n[ALERT] NEW SESSION FOUND!")
        # Update state first to avoid repeat notifications if something fails
        with open(state_file, "w") as f:
            f.write(latest_val)
        
        # Send notifications
        send_notification(latest_text)
        print("[INFO] Process complete. State updated.")
    else:
        print("[INFO] No changes detected. Sleeping.")

if __name__ == "__main__":
    main()
