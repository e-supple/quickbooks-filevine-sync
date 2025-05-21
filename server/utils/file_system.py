from pathlib import Path
import json

def cache_to_file(data: list, cache_dir: Path, filename: str) -> Path:
    """Cache data to a JSON file.

    Args:
        data (list): The data to cache (e.g., list of dictionaries).
        cache_dir (Path): Folder to store the file.
        filename (str): Name of the file (e.g., 'contacts.json').

    Returns:
        Path: The path to the created file.

    Raises:
        OSError: If file writing fails (e.g., permission denied).
    """
    file_path = cache_dir / filename
    cache_dir.mkdir(parents=True, exist_ok=True)  # Create directory if missing
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)  # Serialize data to JSON
        print(f"Data cached to file: {file_path}")
        return file_path
    except OSError as e:
        print(f"Failed to cache data to {file_path}: {e}")
        raise