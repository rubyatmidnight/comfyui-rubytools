"""
Simple text and file utility nodes.
"""
from pathlib import Path
import hashlib
import re
import json

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


def _hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _resolve_source_path(image_path):
    src = Path(image_path).expanduser()
    if not src.is_absolute():
        src = Path.cwd() / src
    return src.resolve()


class TextLoad:
    """Load text from input/output files."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("STRING", {"default": "notes.txt", "tooltip": "File name to read"}),
            },
            "optional": {
                "location": (["input", "output"], {"default": "input", "tooltip": "Base Comfy folder to read from"}),
                "subfolder": ("STRING", {"default": "", "tooltip": "Optional folder under base location"}),
                "missing_ok": ("BOOLEAN", {"default": True, "tooltip": "Return empty text when missing"}),
                "encoding": ("STRING", {"default": "utf-8", "tooltip": "Text encoding for file read"}),
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
                "text": ("STRING", {"multiline": True, "default": "", "tooltip": "Text content to save"}),
                "filename": ("STRING", {"default": "notes.txt", "tooltip": "File name to write"}),
            },
            "optional": {
                "location": (["input", "output"], {"default": "output", "tooltip": "Base Comfy folder to write to"}),
                "subfolder": ("STRING", {"default": "", "tooltip": "Optional folder under base location"}),
                "append": ("BOOLEAN", {"default": False, "tooltip": "Append to file instead of overwrite"}),
                "ensure_newline": ("BOOLEAN", {"default": True, "tooltip": "Add trailing newline if missing"}),
                "encoding": ("STRING", {"default": "utf-8", "tooltip": "Text encoding for file write"}),
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
                "text": ("STRING", {"multiline": True, "default": "", "tooltip": "Text to echo to UI"}),
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
                "location": (["input", "output"], {"default": "input", "tooltip": "Base Comfy folder to scan"}),
                "subfolder": ("STRING", {"default": "", "tooltip": "Folder to scan inside base"}),
                "patterns": ("STRING", {"default": "*.png;*.jpg;*.jpeg;*.webp;*.bmp", "tooltip": "Semicolon-separated glob patterns"}),
            },
            "optional": {
                "start_index": ("INT", {"default": 0, "min": 0, "max": 0xffffffff, "tooltip": "Starting file index for sequence"}),
                "step": ("INT", {"default": 1, "min": 1, "max": 0xffffffff, "tooltip": "Index increment per execution"}),
                "auto_increment": ("BOOLEAN", {"default": True, "tooltip": "Advance index automatically each run"}),
                "reset": ("BOOLEAN", {"default": False, "tooltip": "Reset sequence index to start_index"}),
                "loop": ("BOOLEAN", {"default": True, "tooltip": "Wrap around when index exceeds files"}),
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
                "text": ("STRING", {"multiline": True, "default": "", "tooltip": "Input text to test against patterns"}),
                "default_value": ("STRING", {"default": "", "tooltip": "Fallback output when no match"}),
            },
            "optional": {
                "pattern_1": ("STRING", {"default": "", "tooltip": "Regex for rule 1"}),
                "value_1": ("STRING", {"default": "", "tooltip": "Output for rule 1"}),
                "pattern_2": ("STRING", {"default": "", "tooltip": "Regex for rule 2"}),
                "value_2": ("STRING", {"default": "", "tooltip": "Output for rule 2"}),
                "pattern_3": ("STRING", {"default": "", "tooltip": "Regex for rule 3"}),
                "value_3": ("STRING", {"default": "", "tooltip": "Output for rule 3"}),
                "pattern_4": ("STRING", {"default": "", "tooltip": "Regex for rule 4"}),
                "value_4": ("STRING", {"default": "", "tooltip": "Output for rule 4"}),
                "pattern_5": ("STRING", {"default": "", "tooltip": "Regex for rule 5"}),
                "value_5": ("STRING", {"default": "", "tooltip": "Output for rule 5"}),
                "match_mode": (["search", "fullmatch"], {"default": "search", "tooltip": "search finds anywhere; fullmatch requires full string"}),
                "case_insensitive": ("BOOLEAN", {"default": True, "tooltip": "Ignore case when matching"}),
                "multiline": ("BOOLEAN", {"default": False, "tooltip": "Enable ^ and $ per line"}),
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
    """Cache images by content. With image_path, hash is sha256 of file bytes (Hydrus-compatible)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "Image tensor to hash"}),
            },
            "optional": {
                "image_path": ("STRING", {"default": "", "tooltip": "Source file on disk; if set, hash is sha256 of file bytes, not the tensor"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "hash")
    FUNCTION = "cache"
    CATEGORY = "Ruby's Nodes/Utility"

    @classmethod
    def IS_CHANGED(cls, image, **kwargs):
        return _hash_image(image)

    def cache(self, image, image_path=""):
        if image_path:
            return (image, _hash_file(_resolve_source_path(image_path)))
        return (image, _hash_image(image))


class AutoTagConcat:
    """Append filename and tags."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("STRING", {"default": "", "tooltip": "Image file name for tag line"}),
                "tags": ("STRING", {"default": "", "tooltip": "Tag list to wrap in braces"}),
                "target_filename": ("STRING", {"default": "tags.txt", "tooltip": "Destination text file name"}),
            },
            "optional": {
                "location": (["input", "output"], {"default": "output", "tooltip": "Base Comfy folder to write to"}),
                "subfolder": ("STRING", {"default": "", "tooltip": "Optional folder under base location"}),
                "append": ("BOOLEAN", {"default": True, "tooltip": "Append line instead of overwrite"}),
                "ensure_newline": ("BOOLEAN", {"default": True, "tooltip": "Add trailing newline if missing"}),
                "encoding": ("STRING", {"default": "utf-8", "tooltip": "Text encoding for file write"}),
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


class TagManifestAppend:
    """Append {hash, path, tags} JSONL keyed by file-byte sha256. Never modifies the image."""

    _seen = {}  # manifest path -> set of hashes

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_path": ("STRING", {"default": "", "tooltip": "Source file on disk; hashed as-is"}),
                "tags": ("STRING", {"default": "", "tooltip": "Comma-separated tag string from tagger"}),
                "manifest_path": ("STRING", {"default": "textfiles/manifest.jsonl", "tooltip": "Relative path under output"}),
            },
            "optional": {
                "model": ("STRING", {"default": "", "tooltip": "Tagger model name, recorded per line"}),
                "skip_duplicate_hash": ("BOOLEAN", {"default": True, "tooltip": "Skip write if hash already in manifest"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("hash", "line", "manifest_path")
    FUNCTION = "append"
    OUTPUT_NODE = True
    CATEGORY = "Ruby's Nodes/IO"

    def _load_seen(self, out):
        key = str(out)
        if key not in self._seen:
            seen = set()
            if out.exists():
                with open(out, encoding="utf-8") as handle:
                    for raw in handle:
                        raw = raw.strip()
                        if not raw:
                            continue
                        try:
                            seen.add(json.loads(raw)["hash"])
                        except (json.JSONDecodeError, KeyError):
                            pass
            self._seen[key] = seen
        return self._seen[key]

    def append(self, image_path, tags, manifest_path, model="", skip_duplicate_hash=True):
        src = _resolve_source_path(image_path)
        if not src.exists():
            raise FileNotFoundError(f"Missing image: {src}")
        file_hash = _hash_file(src)

        out = _safe_join(_get_base_dir("output"), manifest_path or "textfiles/manifest.jsonl")
        out.parent.mkdir(parents=True, exist_ok=True)
        seen = self._load_seen(out)

        if skip_duplicate_hash and file_hash in seen:
            return (file_hash, "", str(out))

        record = {
            "hash": file_hash,
            "path": str(src),
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
        }
        if model:
            record["model"] = model
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(out, "a", encoding="utf-8") as handle:
            handle.write(line)
        seen.add(file_hash)
        return (file_hash, line, str(out))


NODE_CLASS_MAPPINGS = {
    "RubyTextLoad": TextLoad,
    "RubyTextSave": TextSave,
    "RubyTextShow": TextShow,
    "RubySequentialImageFromFolder": SequentialImageFromFolder,
    "RubyRegexSwitch": RegexSwitch,
    "RubyImageHashCache": ImageHashCache,
    "RubyAutoTagConcat": AutoTagConcat,
    "RubyTagManifestAppend": TagManifestAppend,
    "RubyEmbedImageTagsAndIndex": TagManifestAppend,  # legacy alias; embed-in-place removed
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyTextLoad": "Text Load",
    "RubyTextSave": "Text Save",
    "RubyTextShow": "Text Show",
    "RubySequentialImageFromFolder": "Sequential Image From Folder",
    "RubyRegexSwitch": "Regex Switch",
    "RubyImageHashCache": "Image Hash Cache",
    "RubyAutoTagConcat": "Auto Tag Concat",
    "RubyTagManifestAppend": "Tag Manifest Append (JSONL)",
    "RubyEmbedImageTagsAndIndex": "Tag Manifest Append (legacy alias)",
}