"""
cli/main.py — Main orchestrator for the BPUT Result Scraper CLI.
Coordinates: prompts → preview → batch fetch → branch detection → Excel save.
"""

import sys
import os
import threading

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_test.combined_resolver import BPUTResolver
from cli.display import (
    print_banner, print_preview_panel, create_results_table,
    add_result_row, print_results_table, print_branch_change_warning,
    print_failed_summary, print_final_summary, print_info, print_success,
    print_error, print_warning, console
)
from cli.prompts import (
    get_user_inputs, confirm_preview, handle_branch_change, ask_retry_failed
)
from cli.fetcher import fetch_single_student, fetch_batch, retry_failed
from cli.excel_writer import ExcelWriter
from rich.live import Live


def extract_student_row_data(result):
    """
    Extract display-friendly data from a fetcher result dict.
    Returns: (roll_no, name, sgpa, branch, semester, grades_dict, subject_codes, subject_name_map, status)
    """
    roll_no = result["roll_no"]
    info = result.get("student_info") or {}
    name = info.get("studentName", "N/A")
    branch = info.get("branchName", "UNKNOWN")
    semester = result.get("semester", "N/A")
    status = result["status"]

    grades_data = result.get("grades_data") or {}
    sgpa = grades_data.get("sgpadetails", {}).get("sgpa", "N/A")
    grades_list = grades_data.get("grades", [])

    # Build grades dict and subject mappings
    grades_dict = {}
    subject_codes = []
    subject_name_map = {}
    for g in grades_list:
        code = g.get("subjectCODE")
        if code:
            grades_dict[code] = g.get("grade", "—")
            if code not in subject_codes:
                subject_codes.append(code)
            subject_name_map[code] = g.get("subjectName", "Unknown")

    return roll_no, name, sgpa, branch, semester, grades_dict, subject_codes, subject_name_map, status


def main():
    print_banner()

    # ── Phase 1: Get user inputs ──
    inputs = get_user_inputs()
    start = inputs["start"]
    end = inputs["end"]
    session = inputs["session"]
    threads = inputs["threads"]

    roll_numbers = [str(r) for r in range(start, end + 1)]
    total = len(roll_numbers)

    # ── Phase 2: Preview first student ──
    print_info(f"Fetching preview for {roll_numbers[0]}...")
    resolver = BPUTResolver(timeout=15)
    preview_result = fetch_single_student(resolver, roll_numbers[0], session)

    if preview_result["status"] == "SUCCESS":
        print_preview_panel(preview_result)
        if not confirm_preview():
            print_warning("Aborted by user.")
            return
    elif preview_result["status"] in ("NO_PROFILE", "NO_RESULTS"):
        print_warning(f"First student ({roll_numbers[0]}): {preview_result['status']} — {preview_result.get('error', '')}")
        print_info("This may be normal (student left/absent). Continuing with batch...")
    else:
        print_error(f"Failed to fetch first student: {preview_result.get('error', 'Unknown error')}")
        print_info("Will still attempt the batch. Continuing...")

    # ── Phase 3: Initialize Excel and state ──
    excel = ExcelWriter(session)
    current_branch = None
    current_semester = None
    current_subject_codes = []
    section_subject_name_map = {}

    # Collect all results in order (we need sorted output)
    all_results_by_roll = {}
    failed_results = []
    completed_count = 0
    results_lock = threading.Lock()

    # Track the index for display
    display_table = create_results_table()
    row_index = 0

    # ── Phase 4: Batch fetch ──
    print_info(f"Starting batch fetch: {total} students with {threads} threads...")
    console.print()

    # Include the preview result in the batch
    all_results_by_roll[roll_numbers[0]] = preview_result
    completed_count = 1

    # Fetch remaining students
    remaining = roll_numbers[1:] if len(roll_numbers) > 1 else []

    if remaining:
        recent_results = [(1, preview_result)]
        live_row_index = 1
        live_lock = threading.Lock()

        live_table = create_results_table()
        r_roll, r_name, r_sgpa, r_branch, r_sem, r_grades, r_codes, r_name_map, r_status = extract_student_row_data(preview_result)
        add_result_row(live_table, 1, r_roll, r_name, r_sgpa, r_status)

        with Live(live_table, refresh_per_second=4, console=console) as live:
            def on_result(result):
                nonlocal live_row_index, completed_count
                with live_lock:
                    completed_count += 1
                    live_row_index += 1
                    recent_results.append((live_row_index, result))
                    if len(recent_results) > 5:
                        recent_results.pop(0)
                    
                    # Recreate table with only the last 5 results to save CPU
                    new_table = create_results_table()
                    for idx, res in recent_results:
                        r_roll, r_name, r_sgpa, r_branch, r_sem, r_grades, r_codes, r_name_map, r_status = extract_student_row_data(res)
                        add_result_row(new_table, idx, r_roll, r_name, r_sgpa, r_status)
                    
                    live.update(new_table)

            batch_results, batch_failed = fetch_batch(
                resolver, remaining, session, threads, on_result
            )
        for r in batch_results:
            all_results_by_roll[r["roll_no"]] = r
        failed_results = batch_failed

    # ── Phase 5: Process results in sorted order with branch detection ──
    sorted_rolls = sorted(all_results_by_roll.keys())
    stop_processing = False

    for roll in sorted_rolls:
        if stop_processing:
            break

        result = all_results_by_roll[roll]
        row_index += 1

        roll_no, name, sgpa, branch, semester, grades_dict, subject_codes, subject_name_map, status = \
            extract_student_row_data(result)

        # Add to display table
        add_result_row(display_table, row_index, roll_no, name, sgpa, status)

        # Skip non-successful students for Excel (no grades to write)
        if status != "SUCCESS":
            continue

        # ── Branch change detection ──
        if current_branch is not None and branch != current_branch:
            # First, write footer for the previous section
            excel.write_subject_footer()

            # Show current table progress
            print_results_table(display_table)

            # Alert user
            print_branch_change_warning(current_branch, branch, roll_no)
            choice = handle_branch_change(current_branch, branch)

            if choice == 1:
                # Stop and save
                print_info("Stopping and saving current data...")
                stop_processing = True
                continue
            elif choice == 2:
                # New section in same sheet
                current_branch = branch
                current_semester = semester
                current_subject_codes = subject_codes
                section_subject_name_map = subject_name_map
                excel.start_branch_section(branch, semester, subject_codes, subject_name_map)
            elif choice == 3:
                # New sheet tab
                short_branch = branch.split("(")[-1].replace(")", "").strip()[:20]
                excel.new_sheet(f"{short_branch} {semester}")
                current_branch = branch
                current_semester = semester
                current_subject_codes = subject_codes
                section_subject_name_map = subject_name_map
                excel.start_branch_section(branch, semester, subject_codes, subject_name_map)
            elif choice == 4:
                # New Excel file entirely
                excel.write_subject_footer()
                excel = excel.create_new_file(session)
                current_branch = branch
                current_semester = semester
                current_subject_codes = subject_codes
                section_subject_name_map = subject_name_map
                excel.start_branch_section(branch, semester, subject_codes, subject_name_map)
            elif choice == 5:
                # Skip this student
                continue

            # Recreate display table for clean output
            display_table = create_results_table()
            row_index = 0
            row_index += 1
            add_result_row(display_table, row_index, roll_no, name, sgpa, status)

        # Initialize first section
        if current_branch is None:
            current_branch = branch
            current_semester = semester
            current_subject_codes = subject_codes
            section_subject_name_map = subject_name_map
            
            # Dynamically name the first sheet
            short_branch = branch.split("(")[-1].replace(")", "").strip()[:20]
            excel.rename_sheet(f"{short_branch} {semester}")
            
            excel.start_branch_section(branch, semester, subject_codes, subject_name_map)

        # Merge any new subject codes we haven't seen yet in this section
        for code in subject_codes:
            if code not in current_subject_codes:
                current_subject_codes.append(code)
                excel.add_new_subject_header(code, subject_name_map.get(code, "Unknown"))
            if code in subject_name_map:
                section_subject_name_map[code] = subject_name_map[code]

        # Write to Excel
        excel.add_student_row(roll_no, name, sgpa, grades_dict)

    # Write the final section's footer
    excel.write_subject_footer()

    # Print the final results table
    print_results_table(display_table)

    # ── Phase 6: Handle failed students ──
    if failed_results:
        print_failed_summary(failed_results)

        if ask_retry_failed(len(failed_results)):
            print_info("Retrying failed students with 30s timeout...")

            retry_table = create_results_table()
            retry_idx = 0

            def on_retry_result(result):
                pass

            retried, still_failed = retry_failed(failed_results, session, on_retry_result)

            for r in retried:
                retry_idx += 1
                r_roll, r_name, r_sgpa, r_branch, r_sem, r_grades, r_codes, r_name_map, r_status = \
                    extract_student_row_data(r)

                add_result_row(retry_table, retry_idx, r_roll, r_name, r_sgpa, r_status)

                if r_status == "SUCCESS":
                    # Check if branch matches current section
                    if r_branch == current_branch:
                        for code in r_codes:
                            if code not in current_subject_codes:
                                current_subject_codes.append(code)
                                excel.add_new_subject_header(code, r_name_map.get(code, "Unknown"))
                            if code in r_name_map:
                                section_subject_name_map[code] = r_name_map[code]
                        excel.add_student_row(r_roll, r_name, r_sgpa, r_grades)
                    # If different branch on retry, just add to current section anyway
                    # (user already decided the branching earlier)

            print_results_table(retry_table)

            if still_failed:
                print_warning(f"{len(still_failed)} student(s) still failed after retry.")
                print_failed_summary(still_failed)

            failed_results = still_failed

    # ── Phase 7: Final save ──
    excel.close()

    success_count = sum(
        1 for r in all_results_by_roll.values()
        if r["status"] in ("SUCCESS",)
    )
    fail_count = len(failed_results)

    print_final_summary(total, success_count, fail_count, excel.filepath)


if __name__ == "__main__":
    main()
