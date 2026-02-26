"""
Simple text and file utility nodes.
"""
from pathlib import Path
import hashlib
import re

try:
    import folder_paths as comfy_paths
    _HAS_COMFY_PATHS = True
except Exception:
    comfy_paths = None
    _HAS_COMFY_PATHS = False


def _get_base_dir(location):
    if location == "input":
        if _HAS_COMFY_PATHS:
            return Path(comfy_paths.get_input_directory())
        return Path(__file__).parent.parent.parent / "input"
    if _HAS_COMFY_PATHS:
        return Path(comfy_paths.get_output_directory())
    return Path(__file__).parent.parent.parent / "output"


def _safe_join(base_dir, *parts):
    candidate = base_dir.joinpath(*[p for p in parts if p])
    base_resolved = base_dir.resolve()
    resolved = candidate.resolve()
    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise ValueError("Path escapes base folder.")
    return resolved


def _split_patterns(patterns_text):
    if not patterns_text:
        return ["*"]
    parts = re.split(r"[;,]+", patterns_text)
    return [p.strip() for p in parts if p.strip()]


def _list_files(base_dir, subfolder, patterns_text):
    folder = _safe_join(base_dir, subfolder)
    if not folder.exists():
        return []
    patterns = _split_patterns(patterns_text)
    files = []
    seen = set()
    for pattern in patterns:
        for match in folder.glob(pattern):
            if match.is_file():
                path = match.resolve()
                if path not in seen:
                    files.append(path)
                    seen.add(path)
    files.sort(key=lambda p: p.name.lower())
    return files


def _blank_image():
    import numpy as np
    import torch
    image = np.zeros((1, 1, 3), dtype=np.float32)
    return torch.from_numpy(image)[None,]


def _load_image(path):
    import numpy as np
    import torch
    from PIL import Image, ImageOps
    image = Image.open(path)
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    arr = np.asarray(image).astype("float32") / 255.0
    return torch.from_numpy(arr)[None,]


def _hash_image(image):
    if hasattr(image, "cpu"):
        data = image.cpu().numpy()
    else:
        data = image
    return hashlib.sha256(data.tobytes()).hexdigest()


class TextLoad:
    """Load text from input/output files."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("STRING", {"default": "notes.txt"}),
            },
            "optional": {
                "location": (["input", "output"], {"default": "input"}),
                "subfolder": ("STRING", {"default": ""}),
                "missing_ok": ("BOOLEAN", {"default": True}),
                "encoding": ("STRING", {"default": "utf-8"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("text", "path", "exists")
    FUNCTION = "load"
    CATEGORY = "Ruby's Nodes/IO"

    def load(self, filename, location="input", subfolder="", missing_ok=True, encoding="utf-8"):
        base_dir = _get_base_dir(location)
        file_path = _safe_join(base_dir, subfolder, filename)
        if not file_path.exists():
            if missing_ok:
                return ("", str(file_path), False)
            raise FileNotFoundError(f"Missing file: {file_path}")
        text = file_path.read_text(encoding=encoding)
        return (text, str(file_path), True)


class TextSave:
    """Save text to input/output files."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "filename": ("STRING", {"default": "notes.txt"}),
            },
            "optional": {
                "location": (["input", "output"], {"default": "output"}),
                "subfolder": ("STRING", {"default": ""}),
                "append": ("BOOLEAN", {"default": False}),
                "ensure_newline": ("BOOLEAN", {"default": True}),
                "encoding": ("STRING", {"default": "utf-8"}),
            },
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("path", "chars_written")
    FUNCTION = "save"
    CATEGORY = "Ruby's Nodes/IO"

    def save(self, text, filename, location="output", subfolder="", append=False,
             ensure_newline=True, encoding="utf-8"):
        base_dir = _get_base_dir(location)
        file_path = _safe_join(base_dir, subfolder, filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = text or ""
        if ensure_newline and payload and not payload.endswith("\n"):
            payload += "\n"
        mode = "a" if append else "w"
        with open(file_path, mode, encoding=encoding) as handle:
            handle.write(payload)
        return (str(file_path), len(payload))


class TextShow:
    """Preview a text string."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("text", "length")
    FUNCTION = "show"
    CATEGORY = "Ruby's Nodes/IO"

    def show(self, text):
        length = len(text or "")
        return {"ui": {"text": [text]}, "result": (text, length)}


class SequentialImageFromFolder:
    """Load images one at a time."""

    _state = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "location": (["input", "output"], {"default": "input"}),
                "subfolder": ("STRING", {"default": ""}),
                "patterns": ("STRING", {"default": "*.png;*.jpg;*.jpeg;*.webp;*.bmp"}),
            },
            "optional": {
                "start_index": ("INT", {"default": 0, "min": 0, "max": 0xffffffff}),
                "step": ("INT", {"default": 1, "min": 1, "max": 0xffffffff}),
                "auto_increment": ("BOOLEAN", {"default": True}),
                "reset": ("BOOLEAN", {"default": False}),
                "loop": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "INT", "STRING")
    RETURN_NAMES = ("image", "filename", "path", "index", "status")
    FUNCTION = "load"
    CATEGORY = "Ruby's Nodes/IO"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def load(self, location, subfolder, patterns, start_index=0, step=1,
             auto_increment=True, reset=False, loop=True):
        base_dir = _get_base_dir(location)
        files = _list_files(base_dir, subfolder, patterns)
        state_key = (str(base_dir), subfolder, patterns)
        if reset or state_key not in self._state:
            self._state[state_key] = start_index
        if not files:
            return (_blank_image(), "", "", -1, "no files")
        idx = self._state[state_key]
        if idx >= len(files):
            if loop:
                idx = start_index % len(files)
            else:
                return (_blank_image(), "", "", -1, "index out of range")
        path = files[idx]
        if auto_increment:
            self._state[state_key] = idx + step
        image = _load_image(path)
        return (image, path.name, str(path), idx, "ok")


class RegexSwitch:
    """Select output by regex."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
                "default_value": ("STRING", {"default": ""}),
            },
            "optional": {
                "pattern_1": ("STRING", {"default": ""}),
                "value_1": ("STRING", {"default": ""}),
                "pattern_2": ("STRING", {"default": ""}),
                "value_2": ("STRING", {"default": ""}),
                "pattern_3": ("STRING", {"default": ""}),
                "value_3": ("STRING", {"default": ""}),
                "pattern_4": ("STRING", {"default": ""}),
                "value_4": ("STRING", {"default": ""}),
                "pattern_5": ("STRING", {"default": ""}),
                "value_5": ("STRING", {"default": ""}),
                "match_mode": (["search", "fullmatch"], {"default": "search"}),
                "case_insensitive": ("BOOLEAN", {"default": True}),
                "multiline": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("STRING", "INT", "STRING", "BOOLEAN")
    RETURN_NAMES = ("value", "match_index", "pattern", "matched")
    FUNCTION = "switch"
    CATEGORY = "Ruby's Nodes/Utility"

    def switch(self, text, default_value, pattern_1="", value_1="", pattern_2="", value_2="",
               pattern_3="", value_3="", pattern_4="", value_4="", pattern_5="", value_5="",
               match_mode="search", case_insensitive=True, multiline=False):
        flags = 0
        if case_insensitive:
            flags |= re.IGNORECASE
        if multiline:
            flags |= re.MULTILINE
        rules = [
            (pattern_1, value_1),
            (pattern_2, value_2),
            (pattern_3, value_3),
            (pattern_4, value_4),
            (pattern_5, value_5),
        ]
        for idx, (pattern, value) in enumerate(rules, start=1):
            if not pattern:
                continue
            regex = re.compile(pattern, flags=flags)
            matched = regex.fullmatch(text) if match_mode == "fullmatch" else regex.search(text)
            if matched:
                return (value, idx, pattern, True)
        return (default_value, 0, "", False)


class ImageHashCache:
    """Cache images by content."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "hash")
    FUNCTION = "cache"
    CATEGORY = "Ruby's Nodes/Utility"

    @classmethod
    def IS_CHANGED(cls, image, **kwargs):
        return _hash_image(image)

    def cache(self, image):
        return (image, _hash_image(image))


class AutoTagConcat:
    """Append filename and tags."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("STRING", {"default": ""}),
                "tags": ("STRING", {"default": ""}),
                "target_filename": ("STRING", {"default": "tags.txt"}),
            },
            "optional": {
                "location": (["input", "output"], {"default": "output"}),
                "subfolder": ("STRING", {"default": ""}),
                "append": ("BOOLEAN", {"default": True}),
                "ensure_newline": ("BOOLEAN", {"default": True}),
                "encoding": ("STRING", {"default": "utf-8"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("line", "path")
    FUNCTION = "append"
    CATEGORY = "Ruby's Nodes/IO"

    def append(self, filename, tags, target_filename, location="output", subfolder="",
               append=True, ensure_newline=True, encoding="utf-8"):
        base_dir = _get_base_dir(location)
        file_path = _safe_join(base_dir, subfolder, target_filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        line = f"[{filename}={{{tags}}}]"
        if ensure_newline and not line.endswith("\n"):
            line += "\n"
        mode = "a" if append else "w"
        with open(file_path, mode, encoding=encoding) as handle:
            handle.write(line)
        return (line, str(file_path))


NODE_CLASS_MAPPINGS = {
    "RubyTextLoad": TextLoad,
    "RubyTextSave": TextSave,
    "RubyTextShow": TextShow,
    "RubySequentialImageFromFolder": SequentialImageFromFolder,
    "RubyRegexSwitch": RegexSwitch,
    "RubyImageHashCache": ImageHashCache,
    "RubyAutoTagConcat": AutoTagConcat,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyTextLoad": "Text Load",
    "RubyTextSave": "Text Save",
    "RubyTextShow": "Text Show",
    "RubySequentialImageFromFolder": "Sequential Image From Folder",
    "RubyRegexSwitch": "Regex Switch",
    "RubyImageHashCache": "Image Hash Cache",
    "RubyAutoTagConcat": "Auto Tag Concat",
}
