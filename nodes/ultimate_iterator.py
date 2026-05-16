"""
Ultimate Iterator nodes.

Lockstep multi-parameter sweeps for sampling workflows. One counter advances
every parameter together: each numeric value linearly interpolates from its
min to its max across `sweep_steps` positions, and the string list cycles
through its lines in the chosen order.
"""
import secrets

_iter_counters = {}
_iter_shuffles = {}


def _lerp_position(min_v, max_v, sweep_steps, position):
    """Linear interpolation across sweep_steps positions. position is 0..sweep_steps-1."""
    if sweep_steps <= 1:
        return min_v
    t = position / (sweep_steps - 1)
    return min_v + (max_v - min_v) * t


def _pick_list_line(lines, mode, key, reset, counter):
    """Pick a line from `lines` using the chosen mode. Returns (text, index)."""
    if not lines:
        return ("", -1)

    if mode == "first":
        idx = 0
    elif mode == "last":
        idx = len(lines) - 1
    elif mode == "increment":
        idx = counter % len(lines)
    elif mode == "decrement":
        idx = (len(lines) - 1) - (counter % len(lines))
    elif mode == "shuffle_no_repeat":
        entry = _iter_shuffles.get(key)
        lines_key = tuple(lines)
        need_new = (
            reset
            or entry is None
            or entry.get("lines") != lines_key
            or entry.get("pos", 0) >= len(lines)
        )
        if need_new:
            order = list(range(len(lines)))
            for i in range(len(order) - 1, 0, -1):
                j = secrets.randbelow(i + 1)
                order[i], order[j] = order[j], order[i]
            entry = {"lines": lines_key, "order": order, "pos": 0}
            _iter_shuffles[key] = entry
        idx = entry["order"][entry["pos"]]
        entry["pos"] += 1
    else:
        idx = secrets.randbelow(len(lines))

    return (lines[idx], int(idx))


def _parse_lines(lines_text, strip_empty=True):
    lines = []
    for ln in lines_text.splitlines():
        if strip_empty:
            ln = ln.strip()
            if not ln:
                continue
        lines.append(ln)
    return lines


def _resolve_counter(slot, auto_slot_attr, auto_increment, reset, iteration):
    """Resolve the shared counter for this node. Returns (counter, key)."""
    key = slot or auto_slot_attr
    if reset and key in _iter_counters:
        _iter_counters[key] = 0
    if reset:
        _iter_shuffles.pop(key, None)

    if auto_increment:
        current = _iter_counters.get(key, 0)
        _iter_counters[key] = current + 1
    else:
        current = iteration
    return current, key


class UltimateIterator:
    """
    Lockstep sweep node. Each run advances one shared counter that drives:
    - a line from a multiline string list
    - seed (base + counter * seed_increment)
    - cfg, denoise, lora model/clip strength (each lerps from its min to max
      across sweep_steps positions; set min == max to lock a value)
    """

    def __init__(self):
        self._auto_slot = secrets.token_hex(8)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lines_text": ("STRING", {"multiline": True, "default": "",
                    "tooltip": "One value per line (prompt fragments, tags, etc.)"}),
                "list_mode": (["increment", "decrement", "shuffle_no_repeat", "random", "first", "last"], {
                    "default": "increment",
                    "tooltip": "How to step through the line list"
                }),
                "base_seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff,
                    "tooltip": "Starting seed"}),
                "seed_increment": ("INT", {"default": 1, "min": 0, "max": 0xffffffff,
                    "tooltip": "How much to add to seed per iteration (0 = fixed seed)"}),
                "sweep_steps": ("INT", {"default": 10, "min": 1, "max": 10000,
                    "tooltip": "Total positions in the numeric sweep before cycling"}),
                "cfg_min": ("FLOAT", {"default": 5.0, "min": 0.0, "max": 100.0, "step": 0.1, "tooltip": "CFG at start of sweep"}),
                "cfg_max": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0, "step": 0.1, "tooltip": "CFG at end of sweep"}),
                "denoise_min": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "Denoise at start of sweep"}),
                "denoise_max": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "Denoise at end of sweep"}),
                "lora_model_min": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.05, "tooltip": "LoRA model strength at start"}),
                "lora_model_max": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.05, "tooltip": "LoRA model strength at end"}),
                "lora_clip_min": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.05, "tooltip": "LoRA CLIP strength at start"}),
                "lora_clip_max": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.05, "tooltip": "LoRA CLIP strength at end"}),
                "auto_increment": ("BOOLEAN", {"default": True, "tooltip": "Auto-advance counter each run"}),
                "reset": ("BOOLEAN", {"default": False, "tooltip": "Reset counter and shuffle state"}),
            },
            "optional": {
                "slot": ("STRING", {"default": "", "tooltip": "Shared state key for syncing with other iterators"}),
                "iteration": ("INT", {"default": 0, "min": 0, "max": 0xffffffff,
                    "tooltip": "Manual iteration index (used when auto_increment is False)"}),
                "strip_empty": ("BOOLEAN", {"default": True, "tooltip": "Trim and drop blank lines"}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "FLOAT", "FLOAT", "FLOAT", "FLOAT", "INT")
    RETURN_NAMES = ("text", "list_index", "seed", "cfg", "denoise",
                    "lora_model_strength", "lora_clip_strength", "iteration")
    FUNCTION = "iterate"
    CATEGORY = "Ruby's Nodes/sampling"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        if kwargs.get("auto_increment", True):
            return float("nan")
        return ""

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    def iterate(self, lines_text, list_mode, base_seed, seed_increment, sweep_steps,
                cfg_min, cfg_max, denoise_min, denoise_max,
                lora_model_min, lora_model_max, lora_clip_min, lora_clip_max,
                auto_increment, reset, slot="", iteration=0, strip_empty=True):

        counter, key = _resolve_counter(slot, self._auto_slot, auto_increment, reset, iteration)

        lines = _parse_lines(lines_text, strip_empty)
        text, list_index = _pick_list_line(lines, list_mode, key, reset, counter)

        position = counter % sweep_steps
        cfg = _lerp_position(cfg_min, cfg_max, sweep_steps, position)
        denoise = _lerp_position(denoise_min, denoise_max, sweep_steps, position)
        lora_model = _lerp_position(lora_model_min, lora_model_max, sweep_steps, position)
        lora_clip = _lerp_position(lora_clip_min, lora_clip_max, sweep_steps, position)

        seed = base_seed + counter * seed_increment

        return (text, list_index, seed, cfg, denoise, lora_model, lora_clip, counter)


class UltimateIteratorAdvanced:
    """
    Extended version of UltimateIterator with sampler-specific sweep params:
    sampling steps, eta, s_noise, sigma_min, sigma_max.
    """

    def __init__(self):
        self._auto_slot = secrets.token_hex(8)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lines_text": ("STRING", {"multiline": True, "default": "",
                    "tooltip": "One value per line"}),
                "list_mode": (["increment", "decrement", "shuffle_no_repeat", "random", "first", "last"], {
                    "default": "increment",
                    "tooltip": "How to step through the line list"
                }),
                "base_seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff,
                    "tooltip": "Starting seed"}),
                "seed_increment": ("INT", {"default": 1, "min": 0, "max": 0xffffffff,
                    "tooltip": "Seed delta per iteration"}),
                "sweep_steps": ("INT", {"default": 10, "min": 1, "max": 10000,
                    "tooltip": "Total positions in the numeric sweep"}),
                "cfg_min": ("FLOAT", {"default": 5.0, "min": 0.0, "max": 100.0, "step": 0.1}),
                "cfg_max": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0, "step": 0.1}),
                "denoise_min": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 1.0, "step": 0.01}),
                "denoise_max": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "lora_model_min": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.05}),
                "lora_model_max": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.05}),
                "lora_clip_min": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.05}),
                "lora_clip_max": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.05}),
                "sampler_steps_min": ("INT", {"default": 20, "min": 1, "max": 1000, "tooltip": "Sampler steps at start"}),
                "sampler_steps_max": ("INT", {"default": 20, "min": 1, "max": 1000, "tooltip": "Sampler steps at end"}),
                "eta_min": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01, "tooltip": "Eta at start"}),
                "eta_max": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01, "tooltip": "Eta at end"}),
                "s_noise_min": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01, "tooltip": "s_noise at start"}),
                "s_noise_max": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.01, "tooltip": "s_noise at end"}),
                "sigma_min_low": ("FLOAT", {"default": 0.0292, "min": 0.0, "max": 1000.0, "step": 0.0001, "tooltip": "sigma_min at start of sweep"}),
                "sigma_min_high": ("FLOAT", {"default": 0.0292, "min": 0.0, "max": 1000.0, "step": 0.0001, "tooltip": "sigma_min at end of sweep"}),
                "sigma_max_low": ("FLOAT", {"default": 14.6146, "min": 0.0, "max": 1000.0, "step": 0.0001, "tooltip": "sigma_max at start of sweep"}),
                "sigma_max_high": ("FLOAT", {"default": 14.6146, "min": 0.0, "max": 1000.0, "step": 0.0001, "tooltip": "sigma_max at end of sweep"}),
                "auto_increment": ("BOOLEAN", {"default": True, "tooltip": "Auto-advance counter each run"}),
                "reset": ("BOOLEAN", {"default": False, "tooltip": "Reset counter and shuffle state"}),
            },
            "optional": {
                "slot": ("STRING", {"default": "", "tooltip": "Shared state key for syncing"}),
                "iteration": ("INT", {"default": 0, "min": 0, "max": 0xffffffff,
                    "tooltip": "Manual iteration index"}),
                "strip_empty": ("BOOLEAN", {"default": True, "tooltip": "Trim and drop blank lines"}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "FLOAT", "FLOAT", "FLOAT", "FLOAT",
                    "INT", "FLOAT", "FLOAT", "FLOAT", "FLOAT", "INT")
    RETURN_NAMES = ("text", "list_index", "seed", "cfg", "denoise",
                    "lora_model_strength", "lora_clip_strength",
                    "steps", "eta", "s_noise", "sigma_min", "sigma_max", "iteration")
    FUNCTION = "iterate"
    CATEGORY = "Ruby's Nodes/sampling"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        if kwargs.get("auto_increment", True):
            return float("nan")
        return ""

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    def iterate(self, lines_text, list_mode, base_seed, seed_increment, sweep_steps,
                cfg_min, cfg_max, denoise_min, denoise_max,
                lora_model_min, lora_model_max, lora_clip_min, lora_clip_max,
                sampler_steps_min, sampler_steps_max, eta_min, eta_max,
                s_noise_min, s_noise_max, sigma_min_low, sigma_min_high,
                sigma_max_low, sigma_max_high,
                auto_increment, reset, slot="", iteration=0, strip_empty=True):

        counter, key = _resolve_counter(slot, self._auto_slot, auto_increment, reset, iteration)

        lines = _parse_lines(lines_text, strip_empty)
        text, list_index = _pick_list_line(lines, list_mode, key, reset, counter)

        position = counter % sweep_steps
        cfg = _lerp_position(cfg_min, cfg_max, sweep_steps, position)
        denoise = _lerp_position(denoise_min, denoise_max, sweep_steps, position)
        lora_model = _lerp_position(lora_model_min, lora_model_max, sweep_steps, position)
        lora_clip = _lerp_position(lora_clip_min, lora_clip_max, sweep_steps, position)
        sampler_steps = int(round(_lerp_position(sampler_steps_min, sampler_steps_max, sweep_steps, position)))
        eta = _lerp_position(eta_min, eta_max, sweep_steps, position)
        s_noise = _lerp_position(s_noise_min, s_noise_max, sweep_steps, position)
        sigma_min = _lerp_position(sigma_min_low, sigma_min_high, sweep_steps, position)
        sigma_max = _lerp_position(sigma_max_low, sigma_max_high, sweep_steps, position)

        seed = base_seed + counter * seed_increment

        return (text, list_index, seed, cfg, denoise, lora_model, lora_clip,
                sampler_steps, eta, s_noise, sigma_min, sigma_max, counter)


NODE_CLASS_MAPPINGS = {
    "RubyUltimateIterator": UltimateIterator,
    "RubyUltimateIteratorAdvanced": UltimateIteratorAdvanced,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyUltimateIterator": "Ultimate Iterator",
    "RubyUltimateIteratorAdvanced": "Ultimate Iterator (Advanced)",
}
