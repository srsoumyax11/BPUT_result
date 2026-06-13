# BPUT Result Scraper Pro — Workspace Documentation 📘

This documentation explains the purpose, inputs, outputs, and roles of each file in the workspace.

---

## 📂 Root Directory Files

### 1. [app.py](file:///d:/WebDev/BPUT result scrapper/app.py)
* **Type**: Flask Web Application Server
* **Purpose**: Serves as the web backend.
* **Key Components**:
  * **Routes**:
    * `/health`: Simple health check.
    * `/api/sessions`: Returns a JSON list of active result sessions crawled from the portal.
    * `/api/reports`: Lists generated Excel files in the `exports/` folder.
    * `/download/<filename>`: Downloads Excel files.
    * `/stream-results`: Main endpoint. Initiates a `ThreadPoolExecutor` to fetch student results in parallel and streams the results in real-time to the frontend using Server-Sent Events (SSE).
  * **Functions**:
    * `fetch_student_with_retry()`: Connects to the BPUT resolver with automated retry logic to handle network timeouts.
    * `generate_excel_report()`: Generates structured Excel spreadsheets from the batch query using `pandas`.

### 2. [scraper.py](file:///d:/WebDev/BPUT result scrapper/scraper.py)
* **Type**: Command Line Interface (CLI) Script
* **Purpose**: Allows users to run a range-based batch results extraction directly from the terminal without opening a browser.
* **Key Components**:
  * `main()`: Prompts for Start Registration No, End Registration No, Session, and Threads. Runs the fetcher and displays text progress.
  * `generate_excel()`: Saves a detailed Excel report to the `exports/` directory.
  * `generate_pdf()`: Generates a landscaped PDF report utilizing `fpdf2` containing basic stats, toppers, and color-coded grades.

### 3. [monitor.py](file:///d:/WebDev/BPUT result scrapper/monitor.py)
* **Type**: Automated Cron/Watcher Bot
* **Purpose**: Crawls the BPUT results home page to monitor if new exam sessions are declared.
* **Key Components**:
  * `send_notification()`: Fires notifications to a custom channel on `ntfy.sh` to trigger push alerts on mobile devices.
  * `main()`: Compares the current session list against the stored value in `api_test/last_session.txt`. If a new option appears, updates the file and alerts the user.

### 4. [requirements.txt](file:///d:/WebDev/BPUT result scrapper/requirements.txt)
* **Purpose**: Lists Python dependencies for installation (`flask`, `pandas`, `openpyxl`, `requests`, `gunicorn`, `bs4`, `fpdf2`).

### 5. [Procfile](file:///d:/WebDev/BPUT result scrapper/Procfile)
* **Purpose**: Configures deployment commands for hosting on Render or Heroku. Defines the command to spin up the web app using `gunicorn`: `web: gunicorn app:app`.

---

## 📂 `api_test` Directory (Scraping Core)

### 1. [combined_resolver.py](file:///d:/WebDev/BPUT result scrapper/api_test/combined_resolver.py)
* **Type**: Core Scraping Engine Module
* **Class**: `BPUTResolver`
* **Purpose**: Coordinates multiple calls to BPUT's internal AJAX JSON endpoints to construct a complete student academic profile in a single merged JSON structure.
* **Key Methods**:
  * `get_student_info(roll_no)`: Queries basic student information (Name, College, Branch, Course) from the `/student-detsils-results` endpoint.
  * `get_result_list(roll_no, session, dob)`: Queries the list of declared semesters for the student from `/student-results-list`.
  * `get_grades(roll_no, session, sem_id)`: Fetches detailed subject-wise grades, grade points, credits, and SGPA for a given semester ID from `/student-results-subjects-list`.
  * `resolve_all(roll_no, session, dob="2005-06-18")`: Main entrypoint. Invokes the above three queries in order, merges the results, and handles exceptions.

* **Response JSON Schema (`resolve_all` Output)**:
  ```json
  {
      "roll_no": "string (student registration number)",
      "session": "string (e.g. 'Odd-(2025-26)')",
      "student_info": {
          "rollNo": "string",
          "studentName": "string",
          "batch": "string",
          "branchId": "string",
          "studentPhoto": "string (filename.jpg)",
          "branchName": "string (e.g. 'B.Tech.(COMPUTER SCIENCE & ENGINEERING)')",
          "courseName": "string (e.g. 'B.Tech')",
          "collegeCode": "string",
          "collegeName": "string",
          "semId": null,
          "maxYear": null,
          "leet": null
      },
      "available_results": [
          {
              "semester": "string (e.g. '5th')",
              "course": "string",
              "semId": "string (e.g. '5')",
              "branchName": "string",
              "rollNo": "string",
              "examSession": "string"
          }
      ],
      "detailed_results": {
          "semId_string": {
              "grades": [
                  {
                      "semester": "string",
                      "course": "string/null",
                      "semId": "string",
                      "branchName": "string/null",
                      "rollNo": "string",
                      "subjectCODE": "string (e.g. 'CSPC3001')",
                      "subjectTP": "string ('T' for Theory, 'P' for Practical)",
                      "subjectName": "string (e.g. 'Theory of Computation')",
                      "subjectCredits": "number (credits value)",
                      "grade": "string (Grade letter: O/E/A/B/C/D/F/M)",
                      "points": "number (grade point mapping)",
                      "creditPoints": "number (points * credits)",
                      "recheck": "number"
                  }
              ],
              "sgpadetails": {
                  "cretits": "number (total credits for the semester)",
                  "totalGradePoints": "number (total credit points earned)",
                  "sgpa": "string (e.g. '6.73')"
              }
          }
      },
      "errors": "array (list of step failures, if any)"
  }
  ```


### 2. [extract_sessions.py](file:///d:/WebDev/BPUT result scrapper/api_test/extract_sessions.py)
* **Type**: Auxiliary Web Scraper
* **Purpose**: Scrapes BPUT homepage HTML (`https://results.bput.ac.in`) using `BeautifulSoup` to locate and parse available options in the session select dropdown, returning a list of dictionaries with text/value pairs.

### 3. [fetch_photo.py](file:///d:/WebDev/BPUT result scrapper/api_test/fetch_photo.py)
* **Type**: Experimental Asset Downloader
* **Purpose**: Tries downloading a student's photo from various guessed directories on BPUT server hostnames (e.g., `bputexam.in`, `bputevaluation.com`, `bput.ac.in`).

### 4. [test_req1.py](file:///d:/WebDev/BPUT result scrapper/api_test/test_req1.py) | [test_req2.py](file:///d:/WebDev/BPUT result scrapper/api_test/test_req2.py) | [test_req3.py](file:///d:/WebDev/BPUT result scrapper/api_test/test_req3.py)
* **Type**: Raw Endpoint Test Scripts
* **Purpose**: Directly execute individual POST queries to BPUT's backend JSON routes using customized headers.
* **Outputs**: Write raw response logs as JSON files to help inspect data format:
  * `test_req1.py` -> saves to `result_req1.json` (List of semesters)
  * `test_req2.py` -> saves to `result_req2.json` (Subject-wise grades)
  * `test_req3.py` -> saves to `result_req3.json` (Student details)

### 5. [req1_resolve.py](file:///d:/WebDev/BPUT result scrapper/api_test/req1_resolve.py) | [req2_resolve.py](file:///d:/WebDev/BPUT result scrapper/api_test/req2_resolve.py) | [req3_resolve.py](file:///d:/WebDev/BPUT result scrapper/api_test/req3_resolve.py)
* **Type**: Refactored API Helper Modules
* **Purpose**: Abstract raw requests into modular, reusable Python functions that parse the BPUT responses and return Python lists or dictionaries. Useful for import by other scripts.

### 6. [last_session.txt](file:///d:/WebDev/BPUT result scrapper/api_test/last_session.txt)
* **Type**: State Storage File
* **Purpose**: Stores the string value representing the latest crawled session (used by `monitor.py` to compare states).

### 7. [portal_home.html](file:///d:/WebDev/BPUT result scrapper/api_test/portal_home.html)
* **Type**: HTML Cache File
* **Purpose**: Stores the raw homepage content fetched from BPUT portal for BeautifulSoup debugging.
