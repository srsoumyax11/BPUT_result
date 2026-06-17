"""
cli/display.py — TUI rendering with Rich library.
Handles all console output: banners, preview panels, live result tables,
error summaries, and final completion panels.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()


def print_banner():
    """Display the application banner."""
    banner_text = Text()
    banner_text.append("  BPUT RESULT SCRAPER ", style="bold white on blue")
    banner_text.append("  CLI v2.0  ", style="bold cyan")
    console.print()
    console.print(Panel(banner_text, border_style="blue", padding=(1, 2)))
    console.print()


def sgpa_color(sgpa_str):
    """Return a Rich style string based on SGPA value."""
    try:
        val = float(sgpa_str)
    except (ValueError, TypeError):
        return "dim"
    if val >= 8.0:
        return "bold green"
    elif val >= 6.0:
        return "bold yellow"
    else:
        return "bold red"


def print_preview_panel(student_data):
    """
    Display a rich panel with the first student's full profile.
    student_data is the dict returned by fetcher.fetch_single_student().
    """
    info = student_data.get("student_info") or {}
    grades_data = student_data.get("grades_data") or {}

    name = info.get("studentName", "N/A")
    college = info.get("collegeName", "N/A")
    branch = info.get("branchName", "N/A")
    semester = student_data.get("semester", "N/A")
    sgpa = grades_data.get("sgpadetails", {}).get("sgpa", "N/A")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="dim", width=12)
    table.add_column("Value", style="bold white")

    table.add_row("Name", name)
    table.add_row("College", college)
    table.add_row("Branch", branch)
    table.add_row("Session", student_data.get("session", "N/A"))
    table.add_row("Semester", semester)
    table.add_row("SGPA", Text(str(sgpa), style=sgpa_color(sgpa)))

    console.print(Panel(
        table,
        title="[bold cyan]📋 Preview — First Student[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    ))


def create_results_table():
    """Create and return a fresh Rich Table for displaying batch results."""
    table = Table(
        title="[bold blue]📊 Batch Results[/bold blue]",
        box=box.ROUNDED,
        show_lines=False,
        header_style="bold white on blue",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Roll No", style="cyan", width=14)
    table.add_column("Name", width=28, no_wrap=True)
    table.add_column("SGPA", justify="center", width=8)
    table.add_column("Status", justify="center", width=12)
    return table


def add_result_row(table, index, roll_no, name, sgpa, status):
    """Add a single result row to the batch results table."""
    # SGPA styling
    if sgpa and sgpa != "N/A":
        sgpa_text = Text(str(sgpa), style=sgpa_color(sgpa))
    else:
        sgpa_text = Text("—", style="dim")

    # Name styling
    if name and name != "N/A":
        name_display = name[:26] + ".." if len(name) > 28 else name
        name_text = Text(name_display)
    else:
        name_text = Text("—", style="dim italic")

    # Status styling
    status_map = {
        "SUCCESS": ("✅", "green"),
        "NO_PROFILE": ("👻 No Profile", "dim"),
        "NO_RESULTS": ("📭 No Results", "yellow"),
        "TIMEOUT": ("⚠️  Timeout", "bold red"),
        "ERROR": ("❌ Error", "bold red"),
    }
    icon, style = status_map.get(status, ("?", "dim"))
    status_text = Text(icon, style=style)

    table.add_row(str(index), str(roll_no), name_text, sgpa_text, status_text)


def print_results_table(table):
    """Print the completed results table to console."""
    console.print()
    console.print(table)
    console.print()


def print_branch_change_warning(old_branch, new_branch, roll_no):
    """Display a warning panel when a branch change is detected."""
    msg = Text()
    msg.append(f"Student {roll_no} belongs to a different branch!\n\n", style="bold")
    msg.append("Current:  ", style="dim")
    msg.append(f"{old_branch}\n", style="bold cyan")
    msg.append("New:      ", style="dim")
    msg.append(f"{new_branch}\n", style="bold yellow")

    console.print(Panel(
        msg,
        title="[bold yellow]⚠️  Branch Change Detected[/bold yellow]",
        border_style="yellow",
        padding=(1, 2)
    ))


def print_failed_summary(failed_list):
    """Display a table of students that failed to fetch."""
    if not failed_list:
        return

    table = Table(
        title=f"[bold red]⚠️  Failed Students ({len(failed_list)})[/bold red]",
        box=box.ROUNDED,
        header_style="bold white on red",
        padding=(0, 1),
    )
    table.add_column("Roll No", style="cyan", width=14)
    table.add_column("Error", width=50)

    for item in failed_list:
        table.add_row(str(item["roll_no"]), Text(item["error"][:48], style="red"))

    console.print()
    console.print(table)
    console.print()


def print_final_summary(total, success, failed, filepath):
    """Display the final summary panel after all work is done."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="dim", width=16)
    table.add_column("Value", style="bold white")

    table.add_row("Total Students", str(total))
    table.add_row("Successful", Text(str(success), style="bold green"))
    table.add_row("Failed", Text(str(failed), style="bold red" if failed > 0 else "bold green"))
    table.add_row("Excel File", Text(filepath, style="bold cyan underline"))

    console.print(Panel(
        table,
        title="[bold green]✅ Batch Complete[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))
    console.print()


def print_progress(current, total, message=""):
    """Print a simple progress line."""
    pct = int((current / total) * 100) if total > 0 else 0
    bar_filled = int(pct / 5)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    console.print(
        f"  [{bar}] {pct}% ({current}/{total}) {message}",
        end="\r", highlight=False
    )


def print_info(message):
    """Print an info message."""
    console.print(f"  [blue]ℹ[/blue]  {message}")


def print_success(message):
    """Print a success message."""
    console.print(f"  [green]✅[/green] {message}")


def print_error(message):
    """Print an error message."""
    console.print(f"  [red]❌[/red] {message}")


def print_warning(message):
    """Print a warning message."""
    console.print(f"  [yellow]⚠️[/yellow]  {message}")
