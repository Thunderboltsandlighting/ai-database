"""
UI Helper module for HVLC_DB.

This module provides enhanced user interface helpers for the command-line,
including colorized output, better error messages, and interactive components.
"""

import os
import sys
import time
import textwrap
import json
from typing import List, Dict, Any, Optional, Union, Tuple
import platform
from datetime import datetime
import logging

from utils.logger import get_logger
from utils.config import get_config

logger = get_logger()
config = get_config()

# Check if we can use colorized output
USE_COLORS = True
if platform.system() == 'Windows':
    try:
        import colorama
        colorama.init()
    except ImportError:
        USE_COLORS = False


# ANSI Color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'


def colorize(text: str, color: str, bold: bool = False) -> str:
    """Colorize text if supported
    
    Args:
        text: Text to colorize
        color: Color to use
        bold: Whether to make text bold
        
    Returns:
        Colorized text
    """
    if not USE_COLORS:
        return text
    
    if bold:
        return f"{Colors.BOLD}{color}{text}{Colors.RESET}"
    else:
        return f"{color}{text}{Colors.RESET}"


def info(message: str) -> None:
    """Print info message
    
    Args:
        message: Message to print
    """
    prefix = colorize("ℹ️  INFO", Colors.BLUE, True)
    print(f"{prefix}: {message}")
    logger.info(message)


def success(message: str) -> None:
    """Print success message
    
    Args:
        message: Message to print
    """
    prefix = colorize("✅ SUCCESS", Colors.GREEN, True)
    print(f"{prefix}: {message}")
    logger.info(message)


def warning(message: str) -> None:
    """Print warning message
    
    Args:
        message: Message to print
    """
    prefix = colorize("⚠️  WARNING", Colors.YELLOW, True)
    print(f"{prefix}: {message}")
    logger.warning(message)


def error(message: str) -> None:
    """Print error message
    
    Args:
        message: Message to print
    """
    prefix = colorize("❌ ERROR", Colors.RED, True)
    print(f"{prefix}: {message}")
    logger.error(message)


def debug(message: str) -> None:
    """Print debug message if in debug mode
    
    Args:
        message: Message to print
    """
    if config.get("logging.level", "INFO").upper() == "DEBUG":
        prefix = colorize("🔍 DEBUG", Colors.MAGENTA, True)
        print(f"{prefix}: {message}")
        logger.debug(message)


def print_header(title: str, width: int = 70) -> None:
    """Print a formatted header
    
    Args:
        title: Header title
        width: Header width
    """
    if USE_COLORS:
        print(colorize("=" * width, Colors.CYAN))
        print(colorize(f"{title.center(width)}", Colors.CYAN, True))
        print(colorize("=" * width, Colors.CYAN))
    else:
        print("=" * width)
        print(title.center(width))
        print("=" * width)


def print_footer(width: int = 70) -> None:
    """Print a formatted footer
    
    Args:
        width: Footer width
    """
    if USE_COLORS:
        print(colorize("=" * width, Colors.CYAN))
    else:
        print("=" * width)


def print_step(step: int, total: int, message: str) -> None:
    """Print a step in a multi-step process
    
    Args:
        step: Current step
        total: Total number of steps
        message: Step message
    """
    prefix = colorize(f"[{step}/{total}]", Colors.BLUE, True)
    print(f"{prefix} {message}")


def print_banner(title: str, version: str = "1.0.0") -> None:
    """Print application banner
    
    Args:
        title: Application title
        version: Application version
    """
    if USE_COLORS:
        banner = f"""
        {colorize('=' * 60, Colors.CYAN)}
        {colorize(title.center(60), Colors.GREEN, True)}
        {colorize(f"v{version}".center(60), Colors.YELLOW)}
        {colorize('=' * 60, Colors.CYAN)}
        """
    else:
        banner = f"""
        {'=' * 60}
        {title.center(60)}
        v{version}
        {'=' * 60}
        """
    
    print(banner)


def print_table(headers: List[str], rows: List[List[Any]], 
                title: str = None, footer: str = None) -> None:
    """Print a formatted table
    
    Args:
        headers: Table headers
        rows: Table rows
        title: Optional table title
        footer: Optional table footer
    """
    if not rows:
        print("No data to display")
        return
    
    # Calculate column widths
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Calculate total width
    total_width = sum(col_widths) + (len(headers) * 3) + 1
    
    # Print title if provided
    if title:
        print_header(title, total_width)
    else:
        print("+" + "-" * (total_width - 2) + "+")
    
    # Print headers
    header_row = "|"
    for i, header in enumerate(headers):
        if USE_COLORS:
            header_text = colorize(str(header).center(col_widths[i]), Colors.BOLD)
        else:
            header_text = str(header).center(col_widths[i])
        header_row += f" {header_text} |"
    print(header_row)
    
    # Print separator
    print("|" + "-" * (total_width - 2) + "|")
    
    # Print rows
    for row in rows:
        row_str = "|"
        for i, cell in enumerate(row):
            row_str += f" {str(cell).ljust(col_widths[i])} |"
        print(row_str)
    
    # Print footer
    print("+" + "-" * (total_width - 2) + "+")
    if footer:
        print(footer)


def print_menu(title: str, options: List[str], 
               show_numbers: bool = True, exit_option: bool = True) -> None:
    """Print a menu of options
    
    Args:
        title: Menu title
        options: Menu options
        show_numbers: Whether to show numbers
        exit_option: Whether to add an exit option
    """
    print_header(title)
    
    for i, option in enumerate(options, 1):
        if show_numbers:
            if USE_COLORS:
                print(f"{colorize(str(i), Colors.YELLOW, True)}. {option}")
            else:
                print(f"{i}. {option}")
        else:
            print(f"- {option}")
    
    if exit_option:
        if show_numbers:
            exit_num = len(options) + 1
            if USE_COLORS:
                print(f"{colorize(str(exit_num), Colors.YELLOW, True)}. Exit")
            else:
                print(f"{exit_num}. Exit")
        else:
            print("- Exit")
    
    print_footer()


def get_menu_choice(options: List[str], prompt: str = "Select an option") -> int:
    """Get user's menu choice
    
    Args:
        options: Menu options
        prompt: Prompt to display
        
    Returns:
        Selected option index (0-based)
    """
    exit_option = len(options) + 1
    
    while True:
        try:
            choice = input(f"{prompt} (1-{exit_option}): ").strip()
            
            if choice.lower() in ('exit', 'quit', 'q'):
                return -1
            
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(options):
                return choice_num - 1  # Convert to 0-based index
            elif choice_num == exit_option:
                return -1  # Exit
            else:
                print(f"Please enter a number between 1 and {exit_option}")
        except ValueError:
            print("Please enter a valid number")


def progress_bar(iteration: int, total: int, prefix: str = '',
                 suffix: str = '', decimals: int = 1, length: int = 50,
                 fill: str = '█') -> None:
    """Print a progress bar
    
    Args:
        iteration: Current iteration
        total: Total iterations
        prefix: Prefix string
        suffix: Suffix string
        decimals: Decimal places for percentage
        length: Character length of bar
        fill: Bar fill character
    """
    percent = f"{(100 * (iteration / float(total))):.{decimals}f}"
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    
    if USE_COLORS:
        # Color the bar based on progress
        if iteration / total < 0.3:
            colored_bar = colorize(bar, Colors.RED)
        elif iteration / total < 0.6:
            colored_bar = colorize(bar, Colors.YELLOW)
        else:
            colored_bar = colorize(bar, Colors.GREEN)
        
        sys.stdout.write(f'\r{prefix} |{colored_bar}| {percent}% {suffix}')
    else:
        sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    
    sys.stdout.flush()
    
    # Print new line on complete
    if iteration == total:
        print()


def spinner(seconds: int, message: str = "Processing") -> None:
    """Show a spinner for the specified number of seconds
    
    Args:
        seconds: Number of seconds to show spinner
        message: Message to display
    """
    spinner_chars = ['|', '/', '-', '\\']
    end_time = time.time() + seconds
    i = 0
    
    try:
        while time.time() < end_time:
            sys.stdout.write(f"\r{message} {spinner_chars[i % len(spinner_chars)]}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        
        sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")
        sys.stdout.flush()
    except KeyboardInterrupt:
        sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")
        sys.stdout.flush()
        print("Operation cancelled")


def confirm(message: str, default: bool = True) -> bool:
    """Ask user for confirmation
    
    Args:
        message: Confirmation message
        default: Default response
        
    Returns:
        True if confirmed, False otherwise
    """
    if default:
        prompt = f"{message} [Y/n]: "
    else:
        prompt = f"{message} [y/N]: "
    
    while True:
        response = input(prompt).strip().lower()
        
        if not response:
            return default
        
        if response in ('y', 'yes'):
            return True
        elif response in ('n', 'no'):
            return False
        else:
            print("Please answer 'y' or 'n'")


def multiline_input(prompt: str = "Enter text (Ctrl+D or Ctrl+Z to finish)") -> str:
    """Get multiline input from user
    
    Args:
        prompt: Prompt to display
        
    Returns:
        Multiline text
    """
    print(prompt)
    lines = []
    
    try:
        while True:
            line = input()
            lines.append(line)
    except (EOFError, KeyboardInterrupt):
        print()  # Add a newline for better formatting
    
    return "\n".join(lines)


def print_help(commands: Dict[str, str], title: str = "Available Commands") -> None:
    """Print help information
    
    Args:
        commands: Dictionary of command: description
        title: Help title
    """
    print_header(title)
    
    max_command_len = max(len(cmd) for cmd in commands.keys())
    
    for command, description in commands.items():
        if USE_COLORS:
            cmd_str = colorize(command.ljust(max_command_len), Colors.GREEN, True)
        else:
            cmd_str = command.ljust(max_command_len)
        
        print(f"  {cmd_str}  {description}")
    
    print_footer()


def print_error_context(error: Exception, context: str = None) -> None:
    """Print error with context
    
    Args:
        error: Exception object
        context: Additional context
    """
    if USE_COLORS:
        error_type = colorize(type(error).__name__, Colors.RED, True)
        error_msg = colorize(str(error), Colors.RED)
    else:
        error_type = type(error).__name__
        error_msg = str(error)
    
    print(f"Error ({error_type}): {error_msg}")
    
    if context:
        print(f"Context: {context}")
    
    # Add logging
    logger.error(f"{type(error).__name__}: {str(error)}")
    if context:
        logger.error(f"Context: {context}")


def handle_error(error: Exception, context: str = None, 
                exit_app: bool = False, error_code: int = 1) -> None:
    """Handle error with appropriate messaging
    
    Args:
        error: Exception object
        context: Additional context
        exit_app: Whether to exit application
        error_code: Exit code if exiting
    """
    print_error_context(error, context)
    
    if exit_app:
        print("Exiting application due to error")
        sys.exit(error_code)


def clear_screen() -> None:
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def wait_for_key(message: str = "Press any key to continue...") -> None:
    """Wait for user to press any key
    
    Args:
        message: Message to display
    """
    if os.name == 'nt':  # Windows
        import msvcrt
        print(message, end='', flush=True)
        msvcrt.getch()
        print()
    else:  # Unix/Linux/MacOS
        input(message)


def print_section(title: str, content: str) -> None:
    """Print a titled section with content
    
    Args:
        title: Section title
        content: Section content
    """
    if USE_COLORS:
        print(f"\n{colorize(title, Colors.CYAN, True)}:")
    else:
        print(f"\n{title}:")
    
    # Wrap and indent content
    wrapper = textwrap.TextWrapper(width=80, initial_indent='  ', subsequent_indent='  ')
    print(wrapper.fill(content))


def print_data_frame(df, max_rows: int = 20, max_cols: int = None) -> None:
    """Print a pandas DataFrame with formatting
    
    Args:
        df: DataFrame to print
        max_rows: Maximum rows to display
        max_cols: Maximum columns to display
    """
    if df.empty:
        print("DataFrame is empty")
        return
    
    # Truncate if needed
    if max_rows and len(df) > max_rows:
        print(f"Showing {max_rows} of {len(df)} rows")
        df_display = df.head(max_rows)
    else:
        df_display = df
    
    if max_cols and len(df.columns) > max_cols:
        print(f"Showing {max_cols} of {len(df.columns)} columns")
        df_display = df_display.iloc[:, :max_cols]
    
    # Convert to string representation
    df_str = df_display.to_string()
    
    # Add colors if supported
    if USE_COLORS:
        # Colorize header row
        lines = df_str.split('\n')
        if len(lines) > 0:
            lines[0] = colorize(lines[0], Colors.CYAN, True)
            df_str = '\n'.join(lines)
    
    print(df_str)
    print(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")


def print_json(data: Dict, indent: int = 2, colorize_output: bool = True) -> None:
    """Print JSON data with optional colorization
    
    Args:
        data: Data to print
        indent: Indentation level
        colorize_output: Whether to colorize output
    """
    json_str = json.dumps(data, indent=indent)
    
    if USE_COLORS and colorize_output:
        # Basic syntax highlighting
        json_str = json_str.replace('"', colorize('"', Colors.GREEN))
        
        # Colorize numbers
        import re
        json_str = re.sub(r'(\b\d+\.?\d*\b)', colorize(r'\1', Colors.BLUE), json_str)
        
        # Colorize true/false/null
        json_str = re.sub(r'\b(true|false|null)\b', colorize(r'\1', Colors.MAGENTA), json_str)
    
    print(json_str)


def format_elapsed_time(seconds: float) -> str:
    """Format elapsed time
    
    Args:
        seconds: Elapsed time in seconds
        
    Returns:
        Formatted time string
    """
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f} µs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} sec"
    else:
        minutes, seconds = divmod(seconds, 60)
        return f"{int(minutes)}m {seconds:.2f}s"


def print_timer(start_time: float, message: str = "Completed in") -> None:
    """Print elapsed time since start_time
    
    Args:
        start_time: Start time (from time.time())
        message: Message to display
    """
    elapsed = time.time() - start_time
    formatted_time = format_elapsed_time(elapsed)
    
    if USE_COLORS:
        time_str = colorize(formatted_time, Colors.YELLOW)
    else:
        time_str = formatted_time
    
    print(f"{message} {time_str}")


def interactive_help() -> None:
    """Show interactive help system"""
    help_topics = {
        "commands": "List available commands",
        "database": "Database connection and management",
        "csv": "CSV file operations",
        "queries": "Writing and executing queries",
        "export": "Exporting data",
        "settings": "Application settings",
        "troubleshooting": "Common issues and solutions"
    }
    
    print_header("Help System")
    print("Welcome to the interactive help system.")
    print("Select a topic to learn more:")
    
    for i, (topic, description) in enumerate(help_topics.items(), 1):
        if USE_COLORS:
            topic_str = colorize(topic, Colors.GREEN, True)
        else:
            topic_str = topic
        print(f"{i}. {topic_str} - {description}")
    
    print(f"{len(help_topics) + 1}. Exit help")
    print_footer()
    
    while True:
        try:
            choice = input("Select a topic (or 'exit'): ").strip()
            
            if choice.lower() in ('exit', 'quit', 'q'):
                break
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(help_topics):
                    topic = list(help_topics.keys())[choice_num - 1]
                    show_help_topic(topic)
                elif choice_num == len(help_topics) + 1:
                    break
                else:
                    print(f"Please enter a number between 1 and {len(help_topics) + 1}")
            except ValueError:
                # Try direct topic name
                if choice in help_topics:
                    show_help_topic(choice)
                else:
                    print(f"Unknown topic: {choice}")
        except (KeyboardInterrupt, EOFError):
            break


def show_help_topic(topic: str) -> None:
    """Show help for a specific topic
    
    Args:
        topic: Help topic
    """
    help_content = {
        "commands": """
Available Commands:
- help: Show this help message
- list: List available tables
- query: Execute a query
- import: Import a CSV file
- export: Export query results
- settings: View or change settings
- exit: Exit the application

You can get more help on any command by typing 'help <command>'.
""",
        "database": """
Database Management:
- The application supports both SQLite and PostgreSQL databases
- Use 'settings database' to view or change database connection settings
- SQLite databases are stored locally as files
- PostgreSQL requires a server connection

Connection String Format:
- SQLite: sqlite:///path/to/database.db
- PostgreSQL: postgresql://username:password@host:port/database

Database Operations:
- Use 'list tables' to see available tables
- Use 'describe <table>' to see table structure
- Use 'backup' to create a database backup
""",
        "csv": """
CSV File Operations:
- Use 'import csv' to import a CSV file into the database
- The system automatically detects CSV formats
- Use 'export csv' to export query results to CSV

CSV Import Options:
- Specify delimiter (default: comma)
- Set header row (default: first row)
- Map columns to database fields
- Skip rows or columns

CSV Export Options:
- Choose output file
- Select delimiter
- Include/exclude headers
- Format dates and numbers
""",
        "queries": """
Query Execution:
- Use 'query' to execute a SQL query
- Use 'save query' to save a query for later use
- Use 'load query' to load a saved query

Query Language:
- Standard SQL syntax is supported
- SELECT, INSERT, UPDATE, DELETE operations
- JOIN, GROUP BY, ORDER BY clauses
- Aggregate functions (COUNT, SUM, AVG, etc.)

Query Examples:
- SELECT * FROM table WHERE column = 'value'
- SELECT column1, column2 FROM table ORDER BY column1
- SELECT COUNT(*) FROM table GROUP BY column
""",
        "export": """
Export Options:
- CSV: Comma-separated values
- JSON: JavaScript Object Notation
- Excel: Microsoft Excel spreadsheet
- HTML: Web page format
- Text: Plain text format

Export Commands:
- 'export csv': Export to CSV file
- 'export json': Export to JSON file
- 'export excel': Export to Excel file
- 'export html': Export to HTML file
- 'export text': Export to text file

Export Settings:
- Output file path
- Format options (delimiter, encoding, etc.)
- Data formatting options
""",
        "settings": """
Application Settings:
- Database connection
- Logging level
- Default export format
- Interface options
- Performance settings

Changing Settings:
- Use 'settings view' to see current settings
- Use 'settings set <key> <value>' to change a setting
- Use 'settings reset' to restore default settings

Settings Location:
- Settings are stored in config.json
- Environment variables can override settings
""",
        "troubleshooting": """
Common Issues:
- Database connection failures
- CSV import errors
- Memory issues with large datasets
- Query timeout problems

Troubleshooting Steps:
1. Check log files for detailed error messages
2. Verify database connection settings
3. Ensure CSV files are properly formatted
4. For large datasets, try processing in smaller chunks
5. Increase timeout settings for complex queries

Getting Help:
- Use 'help' command for built-in documentation
- Check log files in the logs directory
- Run with --debug flag for verbose logging
"""
    }
    
    if topic in help_content:
        print_header(f"Help: {topic.capitalize()}")
        print(help_content[topic].strip())
        print_footer()
    else:
        print(f"No help available for topic: {topic}")


# Tests
if __name__ == "__main__":
    # Test colorized output
    print("Testing UI Helper functions:")
    
    print("\nInfo, Success, Warning, Error:")
    info("This is an info message")
    success("This is a success message")
    warning("This is a warning message")
    error("This is an error message")
    
    print("\nHeader and Footer:")
    print_header("Test Header")
    print("Some content")
    print_footer()
    
    print("\nTable:")
    headers = ["ID", "Name", "Value"]
    rows = [
        [1, "Item 1", 10.5],
        [2, "Item 2", 20.75],
        [3, "Item 3", 30.25]
    ]
    print_table(headers, rows, "Sample Table", "3 items")
    
    print("\nMenu:")
    options = ["Option 1", "Option 2", "Option 3"]
    print_menu("Test Menu", options)
    
    print("\nProgress Bar:")
    total = 50
    for i in range(total + 1):
        progress_bar(i, total, prefix="Progress:", suffix="Complete", length=40)
        time.sleep(0.01)
    
    print("\nSpinner:")
    print("Testing spinner for 3 seconds...")
    spinner(3, "Loading")
    print("Done!")
    
    print("\nJSON:")
    sample_data = {
        "name": "Test",
        "values": [1, 2, 3],
        "nested": {
            "key": "value",
            "enabled": True,
            "count": 42
        }
    }
    print_json(sample_data)
    
    print("\nHelp:")
    commands = {
        "help": "Show help information",
        "query": "Execute a query",
        "exit": "Exit the application"
    }
    print_help(commands)
    
    print("\nTimer:")
    start = time.time()
    time.sleep(1.5)
    print_timer(start)
    
    print("\nUI Helper tests completed")