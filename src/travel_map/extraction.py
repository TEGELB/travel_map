from pathlib import Path
from datetime import datetime

import marko
from marko.block import Heading
from marko.inline import RawText
import pandas as pd

def extract_headings_only(input_path: str, output_path: str) -> None:
    """
    Extracts only headings from a Markdown file and writes them to another file.
    """
    # Read the Markdown content
    input_text = Path(input_path).read_text(encoding='utf-8')

    # Parse the Markdown into an AST
    markdown_ast = marko.parse(input_text)

    # Collect formatted headings
    headings = []
    for node in markdown_ast.children:
        if isinstance(node, Heading):
            # Extract plain text content of heading
            heading_text = ''.join(child.children if hasattr(child, 'children') else child
                                   for child in node.children)
            headings.append(f"{'#' * node.level} {heading_text.strip()}")

    # Write output
    Path(output_path).write_text('\n\n'.join(headings), encoding='utf-8')
    print(f"Headings written to: {output_path}")

def extract_text(node) -> str:
    """
    Recursively extracts plain text from a marko node (including inline formatting).
    """
    if isinstance(node, RawText):
        return node.children
    if hasattr(node, 'children'):
        return ''.join(extract_text(child) for child in node.children)
    return ''

def parse_markdown(filepath: str, skip_first_heading: bool = False, column_map: dict = None) -> pd.DataFrame:
    """
    Parses a Markdown travel log file using marko to extract travel durations grouped by country and city.
    Splits visits to the same location into multiple entries if they appear non-consecutively.

    Parameters:
        filepath (str): Path to the .md file.
        skip_first_heading (bool): Whether to skip the first heading (e.g., title or introduction).
        column_map (dict): Optional mapping of output column names, e.g., {'country': 'Country', 'city': 'City', ...}

    Returns:
        pd.DataFrame: A DataFrame with columns [Country, City, Start, End, Duration] by default.
    """
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    ast = marko.parse(content)

    country = city = None
    date_entries = []
    heading_count = 0

    for node in ast.children:
        if not isinstance(node, Heading):
            continue

        heading_count += 1
        if skip_first_heading and heading_count == 1:
            continue

        level = node.level
        text = extract_text(node).strip()

        if level == 1:
            country = text
            city = None  # reset city
        elif level == 2:
            city = text
        elif level == 3:
            parts = text.split(", ")
            if len(parts) == 2:
                try:
                    date = datetime.strptime(parts[1], "%d.%m.%Y").date()
                    effective_city = city if city else country
                    date_entries.append({
                        "country": country,
                        "city": effective_city,
                        "date": date
                    })
                except ValueError:
                    continue  # malformed date

    # Sentry date entry

    # Sort by date to ensure order
    date_entries.sort(key=lambda x: x["date"])

    # Track city/country transitions
    visits = []
    if not date_entries:
        return pd.DataFrame(columns=column_map.values() if column_map else [])

    prev = date_entries[0]
    start_date = end_date = prev["date"]

    for i in range(1, len(date_entries)):
        entry = date_entries[i]
        is_last = i == len(date_entries) - 1

        if entry["country"] == prev["country"] and entry["city"] == prev["city"] and not is_last:
            end_date = entry["date"]  # extend visit
        else:
            visits.append({
                "country": prev["country"],
                "city": prev["city"],
                "start": start_date,
                "end": end_date,
                "duration": (end_date - start_date).days + 1
            })
            prev = entry
            start_date = end_date = entry["date"]

    # Default column mapping
    default_columns = {
        "country": "Country",
        "city": "City",
        "start": "Start",
        "end": "End",
        "duration": "Duration"
    }

    if column_map:
        columns = column_map
    else:
        columns = default_columns

    # Build DataFrame using column map
    df = pd.DataFrame([
        {
            columns["country"]: visit["country"],
            columns["city"]: visit["city"],
            columns["start"]: visit["start"],
            columns["end"]: visit["end"],
            columns["duration"]: visit["duration"]
        }
        for visit in visits
    ])

    return df