from dataclasses import dataclass, field
from itertools import product
from queue import Queue
from pathlib import Path
import csv
from typing import List, Iterator, Any
from openpyxl import load_workbook, Workbook
import pandas as pd
from work.config.constants import GlobalConfig as GC

@dataclass
class BaseContext:
    """Base context with logging functionality."""
    log_queue: Queue = field(default_factory=Queue)

    def log(self, msg: str) -> None:
        """Add a log message to the queue.

        Args:
            msg (str): The message to be logged.
        """
        self.log_queue.put(msg)

def get_module_path(task_dir: Path) -> str:
    """Generate a module path string from a task directory.

    Args:
        task_dir (Path): The directory path of the task.

    Returns:
        str: The dotted module path relative to ROOT_DIR.
    """
    return f"{GC.ROOT_DIR.name}.{'.'.join(task_dir.relative_to(GC.ROOT_DIR).parts)}"

# --- Data Cleaning Functions ---

def clean_text_series(series: pd.Series) -> pd.Series:
    """Clean a text series by removing leading/trailing spaces, converting to lowercase, and stripping newlines.

    Args:
        series (pd.Series): The pandas Series containing text data.

    Returns:
        pd.Series: The cleaned text series.
    """
    return series.str.strip().str.lower().str.replace(r'\n|\r', '', regex=True)

def remove_duplicates(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Remove duplicate rows based on a specified column, keeping the first occurrence.

    Args:
        df (pd.DataFrame): The input DataFrame.
        column (str): The column name to check for duplicates.

    Returns:
        pd.DataFrame: The DataFrame with duplicates removed.
    """
    return df.drop_duplicates(subset=[column], keep='first')

def fill_missing_values(df: pd.DataFrame, column: str, method: str = 'default') -> pd.DataFrame:
    """Fill missing values in a column with a specified method.

    Args:
        df (pd.DataFrame): The input DataFrame.
        column (str): The column name to fill missing values in.
        method (str): The filling method ('default', 'ffill', or 'mean'). Defaults to 'default'.

    Returns:
        pd.DataFrame: The DataFrame with filled values.

    Raises:
        KeyError: If the specified column is not found in the DataFrame.
    """
    if column not in df.columns:
        raise KeyError(f"Column '{column}' not found in DataFrame")
    if method == 'ffill':
        df[column] = df[column].fillna(method='ffill')
    elif method == 'mean' and pd.api.types.is_numeric_dtype(df[column]):
        df[column] = df[column].fillna(df[column].mean())
    else:
        df[column] = df[column].fillna('N/A')  # Default fallback
    return df

def filter_by_condition(df: pd.DataFrame, column: str, condition: Any) -> pd.DataFrame:
    """Filter rows in a DataFrame based on a condition in a specified column.

    Args:
        df (pd.DataFrame): The input DataFrame.
        column (str): The column name to filter on.
        condition (Any): The value to match in the column.

    Returns:
        pd.DataFrame: The filtered DataFrame.

    Raises:
        KeyError: If the specified column is not found in the DataFrame.
    """
    if column not in df.columns:
        raise KeyError(f"Column '{column}' not found in DataFrame")
    return df[df[column] == condition]

def normalize_numeric(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Normalize a numeric column using z-score (subtract mean, divide by standard deviation).

    Args:
        df (pd.DataFrame): The input DataFrame.
        column (str): The column name to normalize.

    Returns:
        pd.DataFrame: The DataFrame with the normalized column.

    Raises:
        KeyError: If the specified column is not found in the DataFrame.
    """
    if column not in df.columns:
        raise KeyError(f"Column '{column}' not found in DataFrame")
    if pd.api.types.is_numeric_dtype(df[column]):
        df[column] = (df[column] - df[column].mean()) / df[column].std()
    return df

# --- File Iterators ---

def csv_row_iterator(file_path: Path) -> Iterator[dict]:
    """Iterate over rows in a CSV file, yielding each row as a dictionary.

    Args:
        file_path (Path): The path to the CSV file.

    Returns:
        Iterator[dict]: An iterator over rows, with column names as keys.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row

def xlsx_row_iterator(file_path: Path, sheet_name: str = None) -> Iterator[list]:
    """Iterate over rows in an XLSX file, yielding each row as a list.

    Args:
        file_path (Path): The path to the XLSX file.
        sheet_name (str, optional): The name of the sheet to read. Defaults to None (active sheet).

    Returns:
        Iterator[list]: An iterator over rows, with cell values as a list.
    """
    wb = load_workbook(filename=file_path, read_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active
    for row in ws.rows:
        yield [cell.value for cell in row]
    wb.close()

def csv_to_dataframe(file_path: Path) -> pd.DataFrame:
    """Load a CSV file into a pandas DataFrame.

    Args:
        file_path (Path): The path to the CSV file.

    Returns:
        pd.DataFrame: The loaded DataFrame.
    """
    return pd.read_csv(file_path)

def xlsx_to_dataframe(file_path: Path, sheet_name: str = None) -> pd.DataFrame:
    """Load an XLSX file into a pandas DataFrame.

    Args:
        file_path (Path): The path to the XLSX file.
        sheet_name (str, optional): The name of the sheet to read. Defaults to None (first sheet).

    Returns:
        pd.DataFrame: The loaded DataFrame.
    """
    return pd.read_excel(file_path, sheet_name=sheet_name)

# --- File Saving Functions ---

def save_to_csv(df: pd.DataFrame, file_path: Path = None, index: bool = False) -> Path:
    """Save a DataFrame to a CSV file, defaulting to the 'data' directory.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        file_path (Path, optional): The destination file path. Defaults to 'data/output.csv'.
        index (bool): Whether to write row index. Defaults to False.

    Returns:
        Path: The path where the file was saved.
    """
    if file_path is None:
        file_path = GC.ROOT_DIR / "data" / "output.csv"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=index, encoding='utf-8')
    return file_path

def save_to_xlsx(df: pd.DataFrame, file_path: Path = None, sheet_name: str = 'Sheet1') -> Path:
    """Save a DataFrame to an XLSX file, defaulting to the 'data' directory.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        file_path (Path, optional): The destination file path. Defaults to 'data/output.xlsx'.
        sheet_name (str): The name of the sheet. Defaults to 'Sheet1'.

    Returns:
        Path: The path where the file was saved.
    """
    if file_path is None:
        file_path = GC.ROOT_DIR / "data" / "output.xlsx"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(file_path, sheet_name=sheet_name, index=False)
    return file_path

# --- Example Usage (for testing purposes) ---
if __name__ == "__main__":
    # Sample data for demonstration
    data = {
        'name': ['  News\n', 'Article ', ' news '],
        'score': [10, None, 30],
        'type': ['A', 'B', 'A']
    }
    df = pd.DataFrame(data)

    # Apply data cleaning
    df['name'] = clean_text_series(df['name'])
    df = fill_missing_values(df, 'score', method='mean')
    df = remove_duplicates(df, 'name')
    df = normalize_numeric(df, 'score')

    # Save to default 'data' directory
    csv_path = save_to_csv(df)
    xlsx_path = save_to_xlsx(df)

    print(f"Saved to CSV: {csv_path}")
    print(f"Saved to XLSX: {xlsx_path}")

    # Iterate over saved files
    for row in csv_row_iterator(csv_path):
        print(row)

    for row in xlsx_row_iterator(xlsx_path):
        print(row)
