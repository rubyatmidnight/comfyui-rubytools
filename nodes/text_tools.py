"""
Simple text and file utility nodes.
"""
from pathlib import Path
import hashlib
import re
import json
import os
import tempfile
from xml.etree import ElementTree as ET

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


def _to_text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return str(value)


def _safe_xml_tag(key):
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", key or "")
    cleaned = cleaned.strip("_")
    if not cleaned:
        cleaned = "tag_data"
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    return cleaned


def _merge_xmp_metadata(existing_xmp, metadata_key, metadata_value):
    xmp_ns = "adobe:ns:meta/"
    rdf_ns = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    ruby_ns = "urn:comfyui:rubytools"
    ET.register_namespace("x", xmp_ns)
    ET.register_namespace("rdf", rdf_ns)
    ET.register_namespace("rubytools", ruby_ns)
    root = None
    source = _to_text(existing_xmp).strip()
    if source:
        source = re.sub(r"<\?xpacket[^>]*\?>", "", source).strip()
        try:
            root = ET.fromstring(source)
        except Exception:
            root = None
    if root is None:
        root = ET.Element(f"{{{xmp_ns}}}xmpmeta")
    if root.tag == f"{{{rdf_ns}}}RDF":
        rdf_node = root
    else:
        rdf_node = root.find(f"{{{rdf_ns}}}RDF")
        if rdf_node is None:
            rdf_node = ET.SubElement(root, f"{{{rdf_ns}}}RDF")
    desc_node = rdf_node.find(f"{{{rdf_ns}}}Description")
    if desc_node is None:
        desc_node = ET.SubElement(rdf_node, f"{{{rdf_ns}}}Description")
    xml_key = _safe_xml_tag(metadata_key)
    item_tag = f"{{{ruby_ns}}}{xml_key}"
    item_node = desc_node.find(item_tag)
    if item_node is None:
        item_node = ET.SubElement(desc_node, item_tag)
    item_node.text = metadata_value
    item_node.set(f"{{{ruby_ns}}}source_key", metadata_key)
    return ET.tostring(root, encoding="utf-8", xml_declaration=False)


def _parse_user_comment(raw_value):
    text = raw_value
    if isinstance(raw_value, bytes):
        prefixes = (b"ASCII\x00\x00\x00", b"UNICODE\x00", b"JIS\x00\x00\x00\x00\x00")
        for prefix in prefixes:
            if raw_value.startswith(prefix):
                text = raw_value[len(prefix):]
                break
    text = _to_text(text).strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except Exception:
        return {"_legacy_user_comment": text}
    if isinstance(payload, dict):
        return payload
    return {"_legacy_user_comment": text}


def _build_png_save_kwargs(image, metadata_key, metadata_value):
    from PIL import PngImagePlugin
    pnginfo = PngImagePlugin.PngInfo()
    for key, value in image.info.items():
        if key in {"icc_profile", "dpi", "gamma", "transparency", "aspect"}:
            continue
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8")
            except Exception:
                continue
        if isinstance(value, str):
            pnginfo.add_text(key, value)
    pnginfo.add_text(metadata_key, metadata_value)
    save_kwargs = {"pnginfo": pnginfo}
    for keep_key in ("icc_profile", "dpi", "gamma", "transparency"):
        if keep_key in image.info:
            save_kwargs[keep_key] = image.info[keep_key]
    return save_kwargs


def _build_jpeg_save_kwargs(image, metadata_key, metadata_value, jpeg_quality):
    exif_data = image.getexif()
    user_comment = _parse_user_comment(exif_data.get(0x9286))
    user_comment[metadata_key] = metadata_value
    exif_data[0x9286] = json.dumps(user_comment, ensure_ascii=False)
    save_kwargs = {
        "quality": jpeg_quality,
        "exif": exif_data.tobytes(),
        "xmp": _merge_xmp_metadata(image.info.get("xmp"), metadata_key, metadata_value),
    }
    for keep_key in ("icc_profile", "comment", "dpi", "subsampling", "qtables", "optimize"):
        if keep_key in image.info:
            save_kwargs[keep_key] = image.info[keep_key]
    return save_kwargs


def _save_image_atomic(image, destination, format_name, save_kwargs):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=destination.suffix, dir=destination.parent) as tmp_handle:
        tmp_name = tmp_handle.name
    try:
        image.save(tmp_name, format=format_name, **save_kwargs)
        os.replace(tmp_name, destination)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


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
    """Cache images by content."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "Image tensor to hash"}),
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


class EmbedImageTagsAndIndex:
    """Embed image tags and append index."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_path": ("STRING", {"default": "", "tooltip": "Absolute or relative path of image to update"}),
                "tags": ("STRING", {"default": "", "tooltip": "Tags to embed and index"}),
                "metadata_key": ("STRING", {"default": "ruby.tags", "tooltip": "Custom metadata key name"}),
                "index_filename": ("STRING", {"default": "master_tags.txt", "tooltip": "Text index file to append"}),
            },
            "optional": {
                "overwrite_image": ("BOOLEAN", {"default": True, "tooltip": "Write metadata back to source file"}),
                "output_location": (["input", "output"], {"default": "output", "tooltip": "Base folder when overwrite is false"}),
                "output_subfolder": ("STRING", {"default": "", "tooltip": "Folder under output location"}),
                "output_filename": ("STRING", {"default": "", "tooltip": "Optional destination image name"}),
                "index_location": (["input", "output"], {"default": "output", "tooltip": "Base folder for index file"}),
                "index_subfolder": ("STRING", {"default": "", "tooltip": "Folder under index location"}),
                "append_index": ("BOOLEAN", {"default": True, "tooltip": "Append line instead of overwrite"}),
                "ensure_newline": ("BOOLEAN", {"default": True, "tooltip": "Add trailing newline to index line"}),
                "encoding": ("STRING", {"default": "utf-8", "tooltip": "Text encoding for index file"}),
                "separator": ("STRING", {"default": "\t", "tooltip": "Delimiter between filename and tags"}),
                "jpeg_quality": ("INT", {"default": 95, "min": 1, "max": 100, "tooltip": "JPEG quality when rewriting jpg/jpeg"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("saved_image_path", "index_path", "index_line", "embedded")
    FUNCTION = "embed"
    CATEGORY = "Ruby's Nodes/IO"

    def embed(self, image_path, tags, metadata_key, index_filename, overwrite_image=True,
              output_location="output", output_subfolder="", output_filename="",
              index_location="output", index_subfolder="", append_index=True,
              ensure_newline=True, encoding="utf-8", separator="\t", jpeg_quality=95):
        from PIL import Image
        src_path = Path(image_path).expanduser()
        if not src_path.is_absolute():
            src_path = Path.cwd() / src_path
        src_path = src_path.resolve()
        if not src_path.exists():
            raise FileNotFoundError(f"Missing image: {src_path}")
        if overwrite_image:
            dst_path = src_path
        else:
            base_dir = _get_base_dir(output_location)
            dest_name = output_filename or src_path.name
            dst_path = _safe_join(base_dir, output_subfolder, dest_name)
        suffix = src_path.suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg"}:
            raise ValueError("Only PNG/JPG/JPEG are supported.")
        with Image.open(src_path) as image:
            if suffix == ".png":
                save_kwargs = _build_png_save_kwargs(image, metadata_key, tags)
                _save_image_atomic(image, dst_path, "PNG", save_kwargs)
            else:
                work_image = image if image.mode in {"RGB", "L"} else image.convert("RGB")
                save_kwargs = _build_jpeg_save_kwargs(work_image, metadata_key, tags, jpeg_quality)
                _save_image_atomic(work_image, dst_path, "JPEG", save_kwargs)
        index_base = _get_base_dir(index_location)
        index_path = _safe_join(index_base, index_subfolder, index_filename)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_line = f"{dst_path.name}{separator}{tags}"
        if ensure_newline and not index_line.endswith("\n"):
            index_line += "\n"
        mode = "a" if append_index else "w"
        with open(index_path, mode, encoding=encoding) as handle:
            handle.write(index_line)
        return (str(dst_path), str(index_path), index_line, True)


NODE_CLASS_MAPPINGS = {
    "RubyTextLoad": TextLoad,
    "RubyTextSave": TextSave,
    "RubyTextShow": TextShow,
    "RubySequentialImageFromFolder": SequentialImageFromFolder,
    "RubyRegexSwitch": RegexSwitch,
    "RubyImageHashCache": ImageHashCache,
    "RubyAutoTagConcat": AutoTagConcat,
    "RubyEmbedImageTagsAndIndex": EmbedImageTagsAndIndex,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyTextLoad": "Text Load",
    "RubyTextSave": "Text Save",
    "RubyTextShow": "Text Show",
    "RubySequentialImageFromFolder": "Sequential Image From Folder",
    "RubyRegexSwitch": "Regex Switch",
    "RubyImageHashCache": "Image Hash Cache",
    "RubyAutoTagConcat": "Auto Tag Concat",
    "RubyEmbedImageTagsAndIndex": "Embed Image Tags + Index",
}
