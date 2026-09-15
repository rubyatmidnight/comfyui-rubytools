"""
Pager: drop a paper note onto a thermal printer from inside a workflow.

The node never talks to a printer itself. It writes one file into an "inbox"
folder and a small daemon that watches that folder does the printing. That
keeps the node portable: any printer you can drive from a script works, and
ComfyUI never blocks on Bluetooth.

Inbox file format (UTF-8 text, any name, .txt):

    From: Sender name        <- optional header lines, until the first blank line
    Icon: fox                <- optional: fox | cat | none

    Body text. Blank lines make paragraphs.

A .png dropped in the inbox is printed as-is (384 px wide is native for the
57 mm printers this was built for).

Where the inbox lives, in order of precedence:
  1. the node's inbox_path input, if not empty
  2. the RUBY_PAGER_INBOX environment variable
  3. "inbox" in nodes/pager.json (copy pager.example.json and edit)

A sample daemon lives in examples/pager/pager_daemon_example.py.
"""
import json
import os
import secrets
import time
from datetime import datetime
from pathlib import Path

from .utils import resolve_path, safe_filename

CONFIG_FILE = Path(__file__).parent / "pager.json"
ICONS = ["fox", "cat", "none"]
PRINT_WIDTH = 384
ENV_VAR = "RUBY_PAGER_INBOX"


def _load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _inbox_dir(override=""):
    """Resolve the inbox folder from the override, env var, or config file.
    Returns (path, source) so the caller knows whether the config file applies."""
    source, candidate = "input", (override or "").strip()
    if not candidate:
        source, candidate = "env", os.environ.get(ENV_VAR, "").strip()
    if not candidate:
        source, candidate = "config", _load_config().get("inbox", "")
    if not candidate:
        raise RuntimeError(
            "No pager inbox configured. Set inbox_path on the node, the "
            f"{ENV_VAR} environment variable, or 'inbox' in nodes/pager.json "
            "(see pager.example.json)."
        )
    inbox = resolve_path(candidate)
    if not inbox.is_dir():
        raise RuntimeError(f"Pager inbox folder does not exist: {inbox}")
    return inbox, source


def _log_file(inbox, source):
    """The daemon's jsonl log: the configured one when the inbox came from the
    config file, otherwise pager.jsonl next to the inbox folder."""
    configured = _load_config().get("log", "") if source == "config" else ""
    if configured:
        return resolve_path(configured)
    return inbox.parent / "pager.jsonl"


def _stamp():
    """Timestamp plus a short random tag so pages sent in the same second never collide."""
    return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)


def _write_atomic(inbox, name, write):
    """Write to a dot-prefixed temp name and rename, so the daemon never sees
    a half-written file (it skips names starting with '.')."""
    tmp = inbox / f".{name}"
    write(tmp)
    final = inbox / name
    tmp.replace(final)
    return final


def _queue_text(inbox, body, sender, icon):
    name = f"{_stamp()}-{safe_filename(sender) or 'pager'}.txt"
    content = f"From: {sender}\nIcon: {icon}\n\n{body.strip()}\n"

    def write(path):
        path.write_text(content, encoding="utf-8")

    return _write_atomic(inbox, name, write)


def _queue_image(inbox, image_tensor, sender, dither):
    """Take the first image of a ComfyUI IMAGE batch, fit it to the print
    width, convert to 1-bit and queue it as a PNG."""
    import numpy as np
    from PIL import Image

    array = image_tensor[0].detach().cpu().numpy()
    pil = Image.fromarray(np.clip(array * 255.0, 0, 255).astype(np.uint8))
    if pil.width != PRINT_WIDTH:
        height = max(1, round(pil.height * PRINT_WIDTH / pil.width))
        pil = pil.resize((PRINT_WIDTH, height), Image.LANCZOS)
    mono = pil.convert("L").convert("1", dither=Image.FLOYDSTEINBERG if dither else Image.NONE)
    name = f"{_stamp()}-{safe_filename(sender) or 'pager'}.png"

    def write(path):
        mono.save(path, format="PNG")

    return _write_atomic(inbox, name, write)


def _wait_for_result(log_path, names, timeout):
    """Tail the daemon log until every queued file is printed or failed."""
    pending = set(names)
    outcome = {}
    deadline = time.time() + timeout
    offset = log_path.stat().st_size if log_path.is_file() else 0
    while pending and time.time() < deadline:
        if log_path.is_file():
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                handle.seek(offset)
                for line in handle:
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    name = record.get("file")
                    if name in pending and record.get("event") in ("printed", "render_failed"):
                        outcome[name] = record["event"]
                        pending.discard(name)
                    elif name in pending and record.get("event") == "print_failed" and record.get("attempt", 1) >= 3:
                        outcome[name] = "print_failed"
                        pending.discard(name)
                offset = handle.tell()
        if pending:
            time.sleep(1.0)
    for name in pending:
        outcome[name] = "timeout"
    return outcome


class PagerSend:
    """Queue a paper note (and/or an image) for the pager daemon."""

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("status", "queued_files")
    FUNCTION = "send"
    CATEGORY = "Ruby's Nodes/Pager"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "", "tooltip": "Message body. About 40 words fits one strip. Blank lines make paragraphs."}),
                "sender": ("STRING", {"default": "ComfyUI", "tooltip": "Name shown in the printed header"}),
                "icon": (ICONS, {"default": "none", "tooltip": "Small icon printed beside the sender name"}),
                "always_send": ("BOOLEAN", {"default": True, "tooltip": "Send on every run, even if the inputs have not changed since the last run"}),
                "wait_for_print": ("BOOLEAN", {"default": False, "tooltip": "Block until the daemon reports the page printed or failed"}),
                "wait_timeout": ("INT", {"default": 60, "min": 5, "max": 600, "tooltip": "Seconds to wait for the daemon when wait_for_print is on"}),
            },
            "optional": {
                "image": ("IMAGE", {"tooltip": "Optional image to print as its own page, scaled to the strip width"}),
                "dither": ("BOOLEAN", {"default": True, "tooltip": "Dither the image to 1-bit instead of hard thresholding"}),
                "inbox_path": ("STRING", {"default": "", "tooltip": "Inbox folder the pager daemon watches. Leave empty to use the environment variable or pager.json."}),
            },
        }

    @classmethod
    def IS_CHANGED(cls, always_send=True, **kwargs):
        if always_send:
            return float("nan")
        return ""

    def send(self, text, sender, icon, always_send, wait_for_print, wait_timeout, image=None, dither=True, inbox_path=""):
        sender = sender.strip() or "ComfyUI"
        has_text = bool(text.strip())
        if not has_text and image is None:
            raise ValueError("Pager: nothing to send. Give it text, an image, or both.")

        inbox, source = _inbox_dir(inbox_path)
        queued = []
        if has_text:
            queued.append(_queue_text(inbox, text, sender, icon))
        if image is not None:
            queued.append(_queue_image(inbox, image, sender, dither))
        names = [path.name for path in queued]

        if wait_for_print:
            outcome = _wait_for_result(_log_file(inbox, source), names, wait_timeout)
            status = ", ".join(f"{name}: {outcome[name]}" for name in names)
        else:
            status = f"queued {len(names)} page(s) in {inbox}"
        return {"ui": {"text": [status]}, "result": (status, "\n".join(names))}


NODE_CLASS_MAPPINGS = {
    "RubyPagerSend": PagerSend,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyPagerSend": "Pager: Send Page",
}
