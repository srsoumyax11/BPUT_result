"""
cli/prompts.py — User input collection and confirmation dialogs.
All interactive prompts are centralized here to keep main.py clean.
"""

from rich.console import Console
from rich.prompt import Prompt, IntPrompt, Confirm
import datetime

console = Console()

def get_default_session():
    """
    Returns default session based on current date.
    e.g. Month >= 6 -> Even-(2025-26)
         Month < 6 -> Odd-(2025-26)
    """
    now = datetime.datetime.now()
    year = now.year
    month = now.month
    
    session_type = "Even" if month >= 6 else "Odd"
    session_year = f"{year - 1}-{str(year)[-2:]}"
    
    return f"{session_type}-({session_year})"

def get_user_inputs():
    """
    Prompt the user for all required inputs.
    Returns a dict: {start, end, session, threads}
    """
    console.print("  [dim]Enter the extraction parameters below.[/dim]\n")

    # Start Registration
    while True:
        start_str = Prompt.ask("  [cyan]Start Registration No[/cyan]")
        try:
            start = int(start_str.strip())
            break
        except ValueError:
            console.print("  [red]Invalid number. Please enter a numeric registration number.[/red]")

    # End Registration
    while True:
        end_str = Prompt.ask("  [cyan]End Registration No[/cyan]")
        try:
            end = int(end_str.strip())
            if end < start:
                console.print("  [red]End must be >= Start registration number.[/red]")
                continue
            break
        except ValueError:
            console.print("  [red]Invalid number. Please enter a numeric registration number.[/red]")

    # Session
    session = Prompt.ask(
        "  [cyan]Session[/cyan]",
        default=get_default_session()
    )
    session = session.strip()

    # Threads
    threads = IntPrompt.ask("  [cyan]Threads[/cyan]", default=10)

    console.print()
    return {
        "start": start,
        "end": end,
        "session": session,
        "threads": threads,
    }


def confirm_preview():
    """Ask user to confirm after seeing the preview panel."""
    return Confirm.ask("  [bold]Is this correct? Proceed with batch?[/bold]", default=True)


def handle_branch_change(old_branch, new_branch):
    """
    Display branch-change options and return user's choice (1-5).
    """
    console.print()
    console.print("  [bold]What would you like to do?[/bold]\n")
    console.print("  [cyan][1][/cyan] Stop here and save current data")
    console.print("  [cyan][2][/cyan] Start a new section in the same Excel sheet")
    console.print("  [cyan][3][/cyan] Create a new sheet (tab) in the same workbook")
    console.print("  [cyan][4][/cyan] Create a completely new Excel file")
    console.print("  [cyan][5][/cyan] Skip this student and continue")
    console.print()

    while True:
        choice_str = Prompt.ask("  [bold]Your choice[/bold]", choices=["1", "2", "3", "4", "5"], default="2")
        return int(choice_str)


def ask_retry_failed(count):
    """Ask user whether to retry failed students."""
    return Confirm.ask(
        f"  [bold]Retry these {count} failed student(s)?[/bold]",
        default=True
    )
