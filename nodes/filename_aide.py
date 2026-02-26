"""
Filename aide node for ComfyUI.
Automatically generates date-based filenames with session identifiers.
"""
import secrets
from datetime import datetime

# Global state for session tracking
_session_hex = None
_session_counter = 0
_session_date = None


class FilenameAide:
    """
    Generate date-based filenames with automatic session tracking.

    Output format: YYYY\\MMDD\\xx_###
    Example: 2026\\0110\\fa_01, 2026\\0110\\fa_355

    - Year, month, day are auto-generated from current date
    - Session hex (2 chars) is randomly generated once per session
    - Counter increments from 0 each session
    - New session starts on reset or when date changes
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "reset_session": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Reset session to generate new hex ID and restart counter"
                }),
                "prefix": ("STRING", {
                    "default": "",
                    "tooltip": "Optional prefix before the path (e.g., 'output/')"
                }),
                "suffix": ("STRING", {
                    "default": "",
                    "tooltip": "Optional suffix after the counter (e.g., '_final')"
                }),
                "separator": ("STRING", {
                    "default": "\\",
                    "tooltip": "Path separator (default is backslash for Windows)"
                }),
                "counter_padding": ("INT", {
                    "default": 2,
                    "min": 1,
                    "max": 6,
                    "tooltip": "Minimum digits for counter (e.g., 2 = 01, 02... 3 = 001, 002...)"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("filename", "directory", "full_path", "counter")
    FUNCTION = "generate"
    CATEGORY = "Ruby's Nodes/Utility"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Always re-execute to increment counter
        return float("nan")

    def generate(self, reset_session=False, prefix="", suffix="",
                 separator="\\", counter_padding=2):
        global _session_hex, _session_counter, _session_date

        now = datetime.now()
        current_date = now.strftime("%Y%m%d")

        # Check if we need a new session (reset requested or date changed)
        if reset_session or _session_hex is None or _session_date != current_date:
            _session_hex = secrets.token_hex(1)  # 2 hex chars
            _session_counter = 0
            _session_date = current_date

        # Build path components
        year = now.strftime("%Y")
        monthday = now.strftime("%m%d")

        # Format counter with padding
        counter_str = str(_session_counter).zfill(counter_padding)

        # Build the filename: xx_###
        filename = f"{_session_hex}_{counter_str}{suffix}"

        # Build the directory: YYYY\MMDD
        directory = f"{year}{separator}{monthday}"

        # Build full path
        if prefix:
            full_path = f"{prefix}{separator}{directory}{separator}{filename}"
        else:
            full_path = f"{directory}{separator}{filename}"

        # Store current counter before incrementing
        current_counter = _session_counter

        # Increment for next call
        _session_counter += 1

        return (filename, directory, full_path, current_counter)


class FilenameAideManual:
    """
    Manual version of FilenameAide where you can specify the session hex.
    Useful for continuing a specific session or matching existing files.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "session_hex": ("STRING", {
                    "default": "00",
                    "tooltip": "2-character hex identifier for this session"
                }),
                "counter": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffff,
                    "tooltip": "Current counter value"
                }),
            },
            "optional": {
                "prefix": ("STRING", {
                    "default": "",
                    "tooltip": "Optional prefix before the path"
                }),
                "suffix": ("STRING", {
                    "default": "",
                    "tooltip": "Optional suffix after the counter"
                }),
                "separator": ("STRING", {
                    "default": "\\",
                    "tooltip": "Path separator"
                }),
                "counter_padding": ("INT", {
                    "default": 2,
                    "min": 1,
                    "max": 6,
                    "tooltip": "Minimum digits for counter"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("filename", "directory", "full_path")
    FUNCTION = "generate"
    CATEGORY = "Ruby's Nodes/Utility"

    def generate(self, session_hex, counter, prefix="", suffix="",
                 separator="\\", counter_padding=2):
        now = datetime.now()

        # Build path components
        year = now.strftime("%Y")
        monthday = now.strftime("%m%d")

        # Ensure session_hex is only 2 chars
        session_hex = session_hex[:2].lower() if session_hex else "00"

        # Format counter with padding
        counter_str = str(counter).zfill(counter_padding)

        # Build the filename: xx_###
        filename = f"{session_hex}_{counter_str}{suffix}"

        # Build the directory: YYYY\MMDD
        directory = f"{year}{separator}{monthday}"

        # Build full path
        if prefix:
            full_path = f"{prefix}{separator}{directory}{separator}{filename}"
        else:
            full_path = f"{directory}{separator}{filename}"

        return (filename, directory, full_path)


# Node registration
NODE_CLASS_MAPPINGS = {
    "RubyFilenameAide": FilenameAide,
    "RubyFilenameAideManual": FilenameAideManual,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyFilenameAide": "Filename Aide (Auto)",
    "RubyFilenameAideManual": "Filename Aide (Manual)",
}
