"""
Session-based memory nodes for adventure games and persistent state.
Automatically manages file paths in ComfyUI output folder.
"""
from pathlib import Path
from datetime import datetime
import json

# ComfyUI output folder (4 levels up from nodes/memory.py)
COMFY_OUTPUT = Path(__file__).parent.parent.parent.parent / "output"
SESSION_DIR = COMFY_OUTPUT / "adventures"


class SessionMemory:
    """
    File-based memory with automatic session management.
    No manual filenames - just use keys!
    """
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("content", "session_id", "path")
    FUNCTION = "access"
    CATEGORY = "RP/Memory"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "memory_key": ("STRING", {"default": "main"}),
            },
            "optional": {
                "session_id": ("STRING", {"default": ""}),  # empty = auto-generate
                "character_name": ("STRING", {"default": ""}),
                "content": ("STRING", {"multiline": True, "default": ""}),
                "mode": (["read", "write", "append"], {"default": "read"}),
            },
        }

    def access(self, memory_key, session_id="", character_name="", content="", mode="read"):
        # Auto-generate session if not provided
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Build path: output/adventures/{session}/{character}_{key}.txt
        session_path = SESSION_DIR / session_id
        session_path.mkdir(parents=True, exist_ok=True)

        # Safe filename
        safe_key = memory_key.replace("/", "_").replace("\\", "_")
        if character_name:
            safe_char = character_name.replace("/", "_").replace("\\", "_")
            filename = f"{safe_char}_{safe_key}.txt"
        else:
            filename = f"{safe_key}.txt"

        file_path = session_path / filename

        # Handle operations
        if mode == "read":
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
            else:
                content = ""
        elif mode == "write":
            file_path.write_text(content, encoding="utf-8")
        elif mode == "append":
            if file_path.exists():
                existing = file_path.read_text(encoding="utf-8")
                content = existing + "\n" + content
            file_path.write_text(content, encoding="utf-8")

        return (content, session_id, str(file_path))


class MemoryStore:
    """
    Key-value memory store with JSON persistence.
    Like a dictionary that persists across workflow runs!
    """
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("value", "all_keys", "session_id")
    FUNCTION = "store"
    CATEGORY = "RP/Memory"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "key": ("STRING", {"default": ""}),
            },
            "optional": {
                "value": ("STRING", {"multiline": True, "default": ""}),
                "session_id": ("STRING", {"default": "current"}),
                "operation": (["get", "set", "append", "delete", "list_keys"], {"default": "get"}),
            },
        }

    def store(self, key, value="", session_id="current", operation="get"):
        # Session file: output/adventures/{session_id}/memory.json
        session_path = SESSION_DIR / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        memory_file = session_path / "memory.json"

        # Load existing memory
        if memory_file.exists():
            memory = json.loads(memory_file.read_text())
        else:
            memory = {}

        # Operations
        if operation == "get":
            result = memory.get(key, "")
        elif operation == "set":
            memory[key] = value
            memory_file.write_text(json.dumps(memory, indent=2))
            result = value
        elif operation == "append":
            memory[key] = memory.get(key, "") + "\n" + value
            memory_file.write_text(json.dumps(memory, indent=2))
            result = memory[key]
        elif operation == "delete":
            if key in memory:
                del memory[key]
                memory_file.write_text(json.dumps(memory, indent=2))
            result = ""
        elif operation == "list_keys":
            result = ", ".join(memory.keys())
        else:
            result = ""

        all_keys = ", ".join(memory.keys())
        return (result, all_keys, session_id)


class MemoryInit:
    """
    Initialize a new session or connect to existing one.
    Use this at the start of your workflow!
    """
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("session_id", "session_path")
    FUNCTION = "init"
    CATEGORY = "RP/Memory"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "session_name": ("STRING", {"default": ""}),  # custom name, or auto-generate
                "create_new": ("BOOLEAN", {"default": False}),  # force new session
            },
        }

    def init(self, session_name="", create_new=False):
        if create_new or not session_name:
            # Auto-generate timestamped session
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        else:
            session_id = session_name

        session_path = SESSION_DIR / session_id
        session_path.mkdir(parents=True, exist_ok=True)

        return (session_id, str(session_path))


class SimpleMemory:
    """
    General-purpose key-value memory.
    No sessions, just simple storage in output/memory/
    """
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("value", "all_keys")
    FUNCTION = "access"
    CATEGORY = "Utility/Memory"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "key": ("STRING", {"default": ""}),
            },
            "optional": {
                "value": ("STRING", {"multiline": True, "default": ""}),
                "namespace": ("STRING", {"default": "default"}),  # organize by workflow/purpose
                "operation": (["get", "set", "append", "delete", "list_keys", "clear_all"], {"default": "get"}),
            },
        }

    def access(self, key, value="", namespace="default", operation="get"):
        # General memory: output/memory/{namespace}/store.json
        memory_base = COMFY_OUTPUT / "memory" / namespace
        memory_base.mkdir(parents=True, exist_ok=True)
        memory_file = memory_base / "store.json"

        # Load existing memory
        if memory_file.exists():
            memory = json.loads(memory_file.read_text())
        else:
            memory = {}

        # Operations
        if operation == "get":
            result = memory.get(key, "")
        elif operation == "set":
            memory[key] = value
            memory_file.write_text(json.dumps(memory, indent=2))
            result = value
        elif operation == "append":
            memory[key] = memory.get(key, "") + "\n" + value
            memory_file.write_text(json.dumps(memory, indent=2))
            result = memory[key]
        elif operation == "delete":
            if key in memory:
                del memory[key]
                memory_file.write_text(json.dumps(memory, indent=2))
            result = ""
        elif operation == "list_keys":
            result = ", ".join(memory.keys())
        elif operation == "clear_all":
            memory = {}
            memory_file.write_text(json.dumps(memory, indent=2))
            result = "Cleared all keys"
        else:
            result = ""

        all_keys = ", ".join(memory.keys())
        return (result, all_keys)


class SimpleFile:
    """
    Simple file read/write in output folder.
    Use for any text-based data storage.
    """
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("content", "path")
    FUNCTION = "access"
    CATEGORY = "Utility/Memory"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("STRING", {"default": "data.txt"}),
            },
            "optional": {
                "content": ("STRING", {"multiline": True, "default": ""}),
                "subfolder": ("STRING", {"default": "memory"}),  # subfolder in output/
                "mode": (["read", "write", "append"], {"default": "read"}),
            },
        }

    def access(self, filename, content="", subfolder="memory", mode="read"):
        # Build path: output/{subfolder}/{filename}
        base_dir = COMFY_OUTPUT / subfolder
        base_dir.mkdir(parents=True, exist_ok=True)

        # Safe filename (remove path traversal)
        safe_name = filename.replace("/", "_").replace("\\", "_")
        file_path = base_dir / safe_name

        # Operations
        if mode == "read":
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
            else:
                content = ""
        elif mode == "write":
            file_path.write_text(content, encoding="utf-8")
        elif mode == "append":
            if file_path.exists():
                existing = file_path.read_text(encoding="utf-8")
                content = existing + "\n" + content
            file_path.write_text(content, encoding="utf-8")

        return (content, str(file_path))


NODE_CLASS_MAPPINGS = {
    "SessionMemory": SessionMemory,
    "MemoryStore": MemoryStore,
    "MemoryInit": MemoryInit,
    "SimpleMemory": SimpleMemory,
    "SimpleFile": SimpleFile,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SessionMemory": "Session Memory (RP)",
    "MemoryStore": "Memory Store (RP)",
    "MemoryInit": "Memory Init (RP)",
    "SimpleMemory": "Simple Memory",
    "SimpleFile": "Simple File",
}
