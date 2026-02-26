"""
Context builder node for environment/setting/combat/situation.
"""
from pathlib import Path
from .utils import safe_filename

BASE_DIR = Path(__file__).parent.parent / "memory" / "contexts"


def _norm_lines(val):
    if val is None:
        return []
    if isinstance(val, list):
        return [str(v).strip() for v in val if str(v).strip()]
    if isinstance(val, str):
        return [ln.strip() for ln in val.splitlines() if ln.strip()]
    return [str(val).strip()]


def _build_section(title, lines):
    lines = _norm_lines(lines)
    if not lines:
        return ""
    body = "\n".join(f"- {ln}" for ln in lines)
    return f"{title}:\n{body}\n"


class ContextCard:
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("context_text", "context_path")
    FUNCTION = "build"
    CATEGORY = "RP/Context"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "name": ("STRING", {"default": "context", "tooltip": "Context card file name"}),
            },
            "optional": {
                "environment": ("STRING", {"multiline": True, "default": "", "tooltip": "Environment details, one per line"}),
                "setting": ("STRING", {"multiline": True, "default": "", "tooltip": "Setting details, one per line"}),
                "situation": ("STRING", {"multiline": True, "default": "", "tooltip": "Current situation, one per line"}),
                "combat": ("STRING", {"multiline": True, "default": "", "tooltip": "Combat state, one per line"}),
                "objectives": ("STRING", {"multiline": True, "default": "", "tooltip": "Goals, one per line"}),
                "threats": ("STRING", {"multiline": True, "default": "", "tooltip": "Threats, one per line"}),
                "allies": ("STRING", {"multiline": True, "default": "", "tooltip": "Allies, one per line"}),
                "resources": ("STRING", {"multiline": True, "default": "", "tooltip": "Resources, one per line"}),
                "notes": ("STRING", {"multiline": True, "default": "", "tooltip": "Freeform notes, one per line"}),
                "memory_dir": ("STRING", {"default": "", "tooltip": "Optional subfolder under contexts"}),
            },
        }

    def build(
        self,
        name="context",
        environment="",
        setting="",
        situation="",
        combat="",
        objectives="",
        threats="",
        allies="",
        resources="",
        notes="",
        memory_dir="",
    ):
        safe_name = safe_filename(name or "context")
        dir_safe = safe_filename(memory_dir or "")
        base = BASE_DIR if not dir_safe else BASE_DIR / dir_safe
        base.mkdir(parents=True, exist_ok=True)

        context_path = base / f"{safe_name}.txt"

        sections = []
        sections.append(_build_section("Environment", environment))
        sections.append(_build_section("Setting", setting))
        sections.append(_build_section("Situation", situation))
        sections.append(_build_section("Combat", combat))
        sections.append(_build_section("Objectives", objectives))
        sections.append(_build_section("Threats", threats))
        sections.append(_build_section("Allies", allies))
        sections.append(_build_section("Resources", resources))
        sections.append(_build_section("Notes", notes))

        context_text = "\n".join(s for s in sections if s).strip() + "\n"
        context_path.write_text(context_text, encoding="utf-8")

        return (context_text, str(context_path))


NODE_CLASS_MAPPINGS = {
    "ContextCard": ContextCard,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ContextCard": "Context Card (Midnight)",
}
