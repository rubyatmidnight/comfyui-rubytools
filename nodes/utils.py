"""Shared utilities for Ruby's Tools nodes."""
import re


def safe_filename(filename):
    """Only allow safe chars in filename for Windows compatibility."""
    return re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
