from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typing import Any
import json

console = Console()

def console_text_print(text: str, data: Any, bold: bool = False,color: str = "green"):
    def any_to_str(data: Any) -> str:
        try:
            if isinstance(data, list):
                if isinstance(data[0], list):
                    return "\n".join([", ".join(item) for item in data])
                else:
                    return ", ".join(data)
            elif isinstance(data, dict):
                return json.dumps(data)
            else:
                return str(data)
        except Exception as e:
            print(f"Warning: Unable to convert data to string: {e}")
            return ""
            
    """
    A helper function to print formatted text using Rich console.

    Args:
        text (str): The text to be printed.
        format_type (str): The type of formatting to apply. Options: "normal", "panel", "status".
        color (str): The color of the text. Defaults to "white".
        bold (bool): Whether to make the text bold. Defaults to False.

    Returns:
        None
    """
    status_text = Text()
    if bold:
        status_text.append(text, style=f"{color} bold")
    else:
        status_text.append(text, style=f"{color}")
    data_str = any_to_str(data)
    status_text.append(data_str)
    console.print(status_text)


