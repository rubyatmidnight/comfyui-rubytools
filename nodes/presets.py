"""
Preset text nodes for ComfyUI.
Edit presets.json in the nodes folder to add/modify presets.
"""
import json
from pathlib import Path


def load_presets():
    """Load presets from JSON file."""
    presets_file = Path(__file__).parent / "presets.json"
    try:
        with open(presets_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return defaults if file doesn't exist
        return {
            "positive_prompts": {
                "notice": "Use custom_nodes/comfyui-nanoruby/nodes/presets.json to customize your own, this is a default fallback when no presets.json is found.",
                "default": "best quality, masterpiece, highly detailed",
                "anime": "bad anatomy, bad hands, missing fingers, extra digits",
                "photo": "illustration, painting, drawing, art, sketch",
            },
            "styles": {
                "cinematic": "cinematic lighting, dramatic, film grain, movie still",
                "anime": "anime style, cel shaded, vibrant colors",
                "photorealistic": "photorealistic, 8k, highly detailed, sharp focus",
            },
            "custom": {
                "example": "your custom preset here",
            }
        }


class PresetText:
    """
    Select preset text from a configurable list.
    Edit nodes/presets.json to customize presets.
    """

    @classmethod
    def INPUT_TYPES(cls):
        presets = load_presets()
        # Flatten all categories into a single list
        all_presets = []
        for category, items in presets.items():
            for name in items.keys():
                all_presets.append(f"{category}/{name}")

        if not all_presets:
            all_presets = ["(no presets found)"]

        return {
            "required": {
                "preset": (all_presets, {
                    "default": all_presets[0] if all_presets else "",
                    "tooltip": "Choose category/name from presets.json"
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "get_preset"
    CATEGORY = "Ruby's Nodes/utils"

    def get_preset(self, preset):
        presets = load_presets()

        if "/" in preset:
            category, name = preset.split("/", 1)
            if category in presets and name in presets[category]:
                return (presets[category][name],)

        return ("",)


class PresetTextMulti:
    """
    Select and combine multiple presets with a separator.
    Edit nodes/presets.json to customize presets.
    """

    @classmethod
    def INPUT_TYPES(cls):
        presets = load_presets()
        all_presets = ["(none)"]
        for category, items in presets.items():
            for name in items.keys():
                all_presets.append(f"{category}/{name}")

        return {
            "required": {
                "preset_1": (all_presets, {"default": all_presets[0], "tooltip": "First preset to include"}),
                "preset_2": (all_presets, {"default": all_presets[0], "tooltip": "Second preset to include"}),
                "preset_3": (all_presets, {"default": all_presets[0], "tooltip": "Third preset to include"}),
                "preset_4": (all_presets, {"default": all_presets[0], "tooltip": "Fourth preset to include"}),
                "separator": ("STRING", {"default": ", ", "tooltip": "Text inserted between selected presets"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "get_presets"
    CATEGORY = "Ruby's Nodes/utils"

    def get_presets(self, preset_1, preset_2, preset_3, preset_4, separator):
        presets = load_presets()
        results = []

        for preset in [preset_1, preset_2, preset_3, preset_4]:
            if preset == "(none)" or "/" not in preset:
                continue
            category, name = preset.split("/", 1)
            if category in presets and name in presets[category]:
                results.append(presets[category][name])

        return (separator.join(results),)


# Node registration
NODE_CLASS_MAPPINGS = {
    "RubyPresetText": PresetText,
    "RubyPresetTextMulti": PresetTextMulti,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyPresetText": "Preset Text (Midnight)",
    "RubyPresetTextMulti": "Preset Multi Text (4) (Midnight)",
}
