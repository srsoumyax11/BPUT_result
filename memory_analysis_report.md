# BPUT Scraper Comprehensive Vulnerability Report

If this application is run on a low-end laptop (e.g., 2GB or 4GB RAM) and you attempt to scrape a very large batch of students (e.g., 5,000+), there are multiple architectural points where memory leaks, crashes, or severe bottlenecks could occur.

Here is an analysis from multiple points of view (POVs):

## 1. Network & API (The Biggest Culprit)

**The Issue:** In `api_test/combined_resolver.py`, the code uses `requests.post(...)` for every single request instead of pooling connections. Furthermore, it hits the BPUT servers as fast as possible with no rate-limiting.
**The Risk:**

- **Socket Exhaustion:** Python opens and destroys hundreds of TCP network sockets rapidly. On a low-end machine, the OS might run out of available socket buffers, leading to sudden crashes or `Connection Refused` errors.
- **IP Ban:** Hitting the API 30+ times a second with zero delay can be flagged by the university firewall as a DDoS attack, resulting in a permanent IP block.
  **The Fix:** Use a single `requests.Session()` to pool and reuse TCP connections. Implement a slight random delay (jitter) or a hard rate limit.

## 2. In-Memory Data Accumulation (RAM POV)

**The Issue:** In `cli/main.py`, the scraper fetches all student data and stores the *entire* raw JSON response (which includes heavy base64 profile pictures) inside the `all_results_by_roll` dictionary.
**The Risk:** If you scrape 5,000 students, keeping thousands of massive nested dictionaries alive in RAM at the exact same time will almost certainly trigger an Out-Of-Memory (OOM) crash on a 2GB RAM laptop.
**The Fix:** Implement a stream-oriented approach. As soon as a student is fetched, immediately extract their grades, write them to Excel, and `del` the raw JSON data from memory.

## 3. High Thread Counts & CPU Bottleneck (CPU POV)

**The Issue:** The application asks the user for the number of threads (default 10) and renders a live ASCII table updating 4 times a second.
**The Risk:**

- **Thread Exhaustion:** A user might type `100` threads. Spinning up 100 threads on a weak CPU will cause intense "context switching", freezing the laptop completely.
- **UI Lag:** Redrawing a 2,000-row terminal table 4 times a second will max out a weak CPU core just calculating the text layout.
  **The Fix:** Enforce a hard limit on threads (e.g., max 15) using `os.cpu_count()`. For the UI, only display the *last 15-20 fetched students* instead of rendering the entire historical list.

## 4. Excel Workbook & Disk I/O (Storage POV)

**The Issue:** The `openpyxl` library keeps the entire Excel workbook in memory until closed. The scraper also saves the file every 10 students (`auto_save_interval = 10`).
**The Risk:**

- **Memory:** `openpyxl`'s DOM model consumes huge amounts of memory for massive spreadsheets.
- **Write Amplification:** Saving a 5MB file every 10 students means rewriting 5MB to your SSD repeatedly. Over 5,000 students, you force your SSD to redundantly rewrite Gigabytes of data, causing SSD wear and slow downs.
  **The Fix:** Increase the auto-save interval to 100 or 500 for large batches. If scaling beyond 10,000 students, switch to `openpyxl.Workbook(write_only=True)` which instantly drops rows from memory (though formatting support is limited).

## 5. State Management & Crash Recovery (State POV)

**The Issue:** The scraper keeps the list of remaining students in memory and only saves the final parsed rows to Excel.
**The Risk:** If the script crashes at student 9,999 due to a power outage or unhandled error, the entire batch state is lost. There is no persistent queue or log to indicate where to safely resume fetching, forcing the user to manually guess the restart point.
**The Fix:** Implement a checkpoint file (e.g., `progress.json` or SQLite database) that logs the exact roll numbers successfully processed, allowing perfect pause and resume functionality.

## 6. Operating System & File Locking (OS POV)

**The Issue:** At the end of the batch (`Phase 7`), the script calls `excel.close()` which unconditionally runs `wb.save(filepath)` without catching errors.
**The Risk:** If the user currently has the `BPUT_Even_2026.xlsx` file open in Microsoft Excel to watch it live, Windows actively locks the file. The final save attempt will throw a fatal `PermissionError`, instantly crashing the script and destroying the final generated footer and any unsaved data.
**The Fix:** Wrap the final `wb.save()` in a `try/except PermissionError` block and prompt the user: *"File is locked by another program. Please close it and press Enter to retry saving."*

---

## 📊 Final Summary Table

| Category (POV)                  | The Issue                                                        | The Risk                                                           | The Recommended Fix                                                | Done |
| :------------------------------ | :--------------------------------------------------------------- | :----------------------------------------------------------------- | :----------------------------------------------------------------- | ---- |
| **Network (Connections)** | Re-creating TCP sockets for every `requests.post()`            | TCP Socket exhaustion; OS throws `Connection Refused`.           | Implement `requests.Session()` to pool and reuse connections.    | ✅   |
| **Network (API Abuse)**   | Zero throttling/delay between threads                            | University firewall flags traffic as a DDoS attack (IP Ban).       | Add artificial jitter and strict rate-limiting (e.g., 5 req/sec).  |      |
| **Memory (RAM)**          | Holding 5000+ raw JSON profiles in `all_results_by_roll`       | Out-Of-Memory (OOM) crash as base64 images fill up RAM.            | Stream rows to Excel immediately;`del` the JSON object from RAM. | ✅   |
| **CPU (Threading)**       | Allowing user to input unlimited max threads                     | Extreme context switching freezes the operating system.            | Cap maximum threads to `os.cpu_count() * 2`.                     | ✅   |
| **CPU (UI Render)**       | Redrawing a massive live table 4 times a second                  | Maxes out CPU core calculating ASCII borders; terminal lags.       | Only display the last 15-20 rows in the live progress table.       | ✅   |
| **Disk (Storage I/O)**    | Saving the entire Excel file every 10 students                   | Severe SSD Write Amplification; degrades disk lifespan.            | Increase `auto_save_interval` to 250+ for large batches.         |      |
| **Disk (openpyxl RAM)**   | Standard `Workbook` holds all cell data in memory indefinitely | OOM crash when creating sheets with 10,000+ formatted rows.        | Switch to `write_only=True` mode for extreme batch sizes.        |      |
| **State (Resume Logic)**  | Batch state is strictly in-memory without persistent queues.     | A crash at student 99% loses tracking state; cannot easily resume. | Maintain a `progress.json` state log to track completed rolls.   |      |
| **OS (File Locking)**     | Final `wb.save()` does not catch file lock exceptions.         | `PermissionError` crash and data loss if user has Excel open.    | Catch `PermissionError` and prompt user to close Excel to retry. |      |
| **Network (Retries)**     | `time.sleep(1)` loop when timeouts occur, rather than scaling. | Instantly hitting an overwhelmed server worsens the server lag.    | Implement proper Exponential Backoff (`sleep(2 ** attempt)`).       |✅     |
