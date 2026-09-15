"""Shared utilities for Ruby's Tools nodes."""
import re


def safe_filename(filename):
    """Only allow safe chars in filename for Windows compatibility."""
    return re.sub(r'[^a-zA-Z0-9._-]', '_', filename)


def resolve_path(text):
    """Turn a user-supplied path into a Path that exists on this side of WSL.

    Accepts Windows drive paths (S:/foo) and WSL mounts (/mnt/s/foo) and tries
    the other spelling when the given one is missing, so one config file works
    whether ComfyUI runs under Windows or WSL.
    """
    from pathlib import Path
    import re as _re

    raw = str(text).strip().strip('"')
    path = Path(raw)
    if path.exists():
        return path
    match = _re.match(r"^([A-Za-z]):[\\/](.*)$", raw)
    if match:
        alt = Path("/mnt") / match.group(1).lower() / match.group(2).replace("\\", "/")
        if alt.exists():
            return alt
    match = _re.match(r"^/mnt/([a-zA-Z])/(.*)$", raw)
    if match:
        alt = Path(f"{match.group(1).upper()}:/") / match.group(2)
        if alt.exists():
            return alt
    return path
