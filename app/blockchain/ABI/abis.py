from typing import Any, Dict, List, Union
import json
import pathlib
from functools import lru_cache


def _open_file(filename: str) -> Any:
    """
    Load and parse a JSON file from the same directory as this script.

    Args:
        filename: Name of the JSON file to load

    Returns:
        Parsed JSON content

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    parent_path = pathlib.Path(__file__).parent
    file_path = parent_path / filename

    if not file_path.exists():
        raise FileNotFoundError(f"ABI file not found: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in {filename}: {e.msg}", e.doc, e.pos)


@lru_cache(maxsize=1)
def get_erc20_abi() -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Get the ERC20 token ABI.

    Returns:
        Cached ERC20 ABI definition
    """
    return _open_file("ERC20.json")


@lru_cache(maxsize=1)
def get_multicall_abi() -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Get the Multicall3 contract ABI.

    Returns:
        Cached Multicall3 ABI definition
    """
    return _open_file("MULTICALL3.json")
