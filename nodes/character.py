"""
Character card builder with file outputs.
"""
from pathlib import Path
from .utils import safe_filename

BASE_DIR = Path(__file__).parent.parent / "memory" / "characters"


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


class CharacterCard:
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("card_text", "card_path", "memory_path", "experience_path")
    FUNCTION = "build"
    CATEGORY = "RP/Characters"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "name": ("STRING", {"default": ""}),
            },
            "optional": {
                "species": ("STRING", {"default": ""}),
                "role": ("STRING", {"default": ""}),
                "pronouns": ("STRING", {"default": ""}),
                "age": ("STRING", {"default": ""}),
                "height": ("STRING", {"default": ""}),
                "weight": ("STRING", {"default": ""}),
                "eye_color": ("STRING", {"default": ""}),
                "hair_color": ("STRING", {"default": ""}),
                "skin": ("STRING", {"default": ""}),
                "traits": ("STRING", {"multiline": True, "default": ""}),
                "personality": ("STRING", {"multiline": True, "default": ""}),
                "backstory": ("STRING", {"multiline": True, "default": ""}),
                "abilities": ("STRING", {"multiline": True, "default": ""}),
                "likes": ("STRING", {"multiline": True, "default": ""}),
                "dislikes": ("STRING", {"multiline": True, "default": ""}),
                "notes": ("STRING", {"multiline": True, "default": ""}),
                "memory_entries": ("STRING", {"multiline": True, "default": ""}),
                "experience_entries": ("STRING", {"multiline": True, "default": ""}),
                "memory_dir": ("STRING", {"default": ""}),
            },
        }

    def build(
        self,
        name,
        species="",
        role="",
        pronouns="",
        age="",
        height="",
        weight="",
        eye_color="",
        hair_color="",
        skin="",
        traits="",
        personality="",
        backstory="",
        abilities="",
        likes="",
        dislikes="",
        notes="",
        memory_entries="",
        experience_entries="",
        memory_dir="",
    ):
        safe_name = safe_filename(name or "character")
        dir_safe = safe_filename(memory_dir or "")
        base = BASE_DIR if not dir_safe else BASE_DIR / dir_safe
        base.mkdir(parents=True, exist_ok=True)

        card_path = base / f"{safe_name}.txt"
        memory_path = base / f"{safe_name}_memory.txt"
        experience_path = base / f"{safe_name}_experience.txt"

        sections = []
        header = [
            f"Name: {name}",
            f"Species: {species}",
            f"Role: {role}",
            f"Pronouns: {pronouns}",
            f"Age: {age}",
            f"Height: {height}",
            f"Weight: {weight}",
            f"Eye Color: {eye_color}",
            f"Hair Color: {hair_color}",
            f"Skin: {skin}",
        ]
        sections.append("\n".join(header).strip())
        sections.append(_build_section("Traits", traits))
        sections.append(_build_section("Personality", personality))
        sections.append(_build_section("Backstory", backstory))
        sections.append(_build_section("Abilities", abilities))
        sections.append(_build_section("Likes", likes))
        sections.append(_build_section("Dislikes", dislikes))
        sections.append(_build_section("Notes", notes))
        sections.append(_build_section("Memories", memory_entries))
        sections.append(_build_section("Experience", experience_entries))

        card_text = "\n\n".join(s for s in sections if s).strip() + "\n"

        card_path.write_text(card_text, encoding="utf-8")
        memory_path.write_text(_build_section("Memories", memory_entries), encoding="utf-8")
        experience_path.write_text(_build_section("Experience", experience_entries), encoding="utf-8")

        return (card_text, str(card_path), str(memory_path), str(experience_path))


NODE_CLASS_MAPPINGS = {
    "CharacterCard": CharacterCard,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CharacterCard": "Character Card (Midnight)",
}
