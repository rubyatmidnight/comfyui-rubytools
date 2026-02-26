"""
Type converter and string utility nodes for ComfyUI.
"""
import json
import secrets

# Global counters for iterators
_float_iterator_counter = 0
_int_iterator_counter = 0


class IntToString:
    """Convert an integer to a string."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("INT", {
                    "default": 0,
                    "min": -0xffffffffffffffff,
                    "max": 0xffffffffffffffff,
                    "tooltip": "Integer to convert to text"
                }),
            },
            "optional": {
                "prefix": ("STRING", {"default": "", "tooltip": "Text added before number"}),
                "suffix": ("STRING", {"default": "", "tooltip": "Text added after number"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "convert"
    CATEGORY = "Utility/Convert"

    def convert(self, value, prefix="", suffix=""):
        return (f"{prefix}{value}{suffix}",)


class FloatToString:
    """Convert a float to a string with optional decimal places."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("FLOAT", {
                    "default": 0.0,
                    "min": -1e10,
                    "max": 1e10,
                    "step": 0.001,
                    "tooltip": "Float to convert to text"
                }),
            },
            "optional": {
                "decimal_places": ("INT", {"default": 2, "min": 0, "max": 10, "tooltip": "Digits after decimal point"}),
                "prefix": ("STRING", {"default": "", "tooltip": "Text added before number"}),
                "suffix": ("STRING", {"default": "", "tooltip": "Text added after number"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "convert"
    CATEGORY = "Utility/Convert"

    def convert(self, value, decimal_places=2, prefix="", suffix=""):
        formatted = f"{value:.{decimal_places}f}"
        return (f"{prefix}{formatted}{suffix}",)


class StringConcat3:
    """Concatenate up to 3 strings with an optional separator."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "string_1": ("STRING", {"default": "", "tooltip": "First string segment"}),
                "string_2": ("STRING", {"default": "", "tooltip": "Second string segment"}),
                "string_3": ("STRING", {"default": "", "tooltip": "Third string segment"}),
                "separator": ("STRING", {"default": "", "tooltip": "Inserted between non-empty parts"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "concat"
    CATEGORY = "Utility/Strings"

    def concat(self, string_1="", string_2="", string_3="", separator=""):
        parts = [s for s in [string_1, string_2, string_3] if s]
        return (separator.join(parts),)


class StringConcat4:
    """Concatenate up to 4 strings with an optional separator."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "string_1": ("STRING", {"default": "", "tooltip": "First string segment"}),
                "string_2": ("STRING", {"default": "", "tooltip": "Second string segment"}),
                "string_3": ("STRING", {"default": "", "tooltip": "Third string segment"}),
                "string_4": ("STRING", {"default": "", "tooltip": "Fourth string segment"}),
                "separator": ("STRING", {"default": "", "tooltip": "Inserted between non-empty parts"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "concat"
    CATEGORY = "Utility/Strings"

    def concat(self, string_1="", string_2="", string_3="", string_4="", separator=""):
        parts = [s for s in [string_1, string_2, string_3, string_4] if s]
        return (separator.join(parts),)


class StringConcat6:
    """Concatenate up to 6 strings with an optional separator."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "string_1": ("STRING", {"default": "", "tooltip": "First string segment"}),
                "string_2": ("STRING", {"default": "", "tooltip": "Second string segment"}),
                "string_3": ("STRING", {"default": "", "tooltip": "Third string segment"}),
                "string_4": ("STRING", {"default": "", "tooltip": "Fourth string segment"}),
                "string_5": ("STRING", {"default": "", "tooltip": "Fifth string segment"}),
                "string_6": ("STRING", {"default": "", "tooltip": "Sixth string segment"}),
                "separator": ("STRING", {"default": "", "tooltip": "Inserted between non-empty parts"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "concat"
    CATEGORY = "Utility/Strings"

    def concat(self, string_1="", string_2="", string_3="", string_4="",
               string_5="", string_6="", separator=""):
        parts = [s for s in [string_1, string_2, string_3, string_4, string_5, string_6] if s]
        return (separator.join(parts),)


class MixedConcat4:
    """Concatenate up to 4 values (strings, ints, or floats) with optional separator."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "value_1": ("STRING,INT,FLOAT", {"default": "", "tooltip": "First value to concatenate"}),
                "value_2": ("STRING,INT,FLOAT", {"default": "", "tooltip": "Second value to concatenate"}),
                "value_3": ("STRING,INT,FLOAT", {"default": "", "tooltip": "Third value to concatenate"}),
                "value_4": ("STRING,INT,FLOAT", {"default": "", "tooltip": "Fourth value to concatenate"}),
                "separator": ("STRING", {"default": "", "tooltip": "Inserted between non-empty parts"}),
                "float_decimals": ("INT", {"default": 2, "min": 0, "max": 10, "tooltip": "Decimal places for float values"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "concat"
    CATEGORY = "Utility/Strings"

    # Accept any input type
    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    def concat(self, value_1="", value_2="", value_3="", value_4="",
               separator="", float_decimals=2):
        parts = []
        for v in [value_1, value_2, value_3, value_4]:
            if v is None or v == "":
                continue
            if isinstance(v, float):
                parts.append(f"{v:.{float_decimals}f}")
            else:
                parts.append(str(v))
        return (separator.join(parts),)


class IterateFloat:
    """
    Iterate through float values from min to max.
    Auto-increments each run, cycles back to min after reaching max.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_value": ("FLOAT", {"default": 0.0, "min": -1e10, "max": 1e10, "step": 0.01, "tooltip": "Start of float range"}),
                "max_value": ("FLOAT", {"default": 1.0, "min": -1e10, "max": 1e10, "step": 0.01, "tooltip": "End of float range"}),
                "steps": ("INT", {"default": 10, "min": 1, "max": 1000,
                    "tooltip": "Number of steps from min to max"}),
                "auto_increment": ("BOOLEAN", {"default": True, "tooltip": "Advance iteration automatically each run"}),
                "reset": ("BOOLEAN", {"default": False, "tooltip": "Reset internal counter to zero"}),
            },
            "optional": {
                "iteration": ("INT", {"default": 0, "min": 0, "max": 0xffffffff,
                    "tooltip": "Manual iteration (only used when auto_increment is False)"}),
            }
        }

    RETURN_TYPES = ("FLOAT", "INT")
    RETURN_NAMES = ("value", "iteration")
    FUNCTION = "iterate"
    CATEGORY = "Utility/Iterate"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        if kwargs.get("auto_increment", True):
            return float("nan")
        return ""

    def iterate(self, min_value, max_value, steps, auto_increment, reset, iteration=0):
        global _float_iterator_counter

        if reset:
            _float_iterator_counter = 0

        if auto_increment:
            current = _float_iterator_counter
            _float_iterator_counter += 1
        else:
            current = iteration

        # Cycle through steps
        step_index = current % steps

        # Calculate value
        if steps > 1:
            value = min_value + (step_index * (max_value - min_value) / (steps - 1))
        else:
            value = min_value

        return (value, current)


class IterateInt:
    """
    Iterate through integer values from min to max.
    Auto-increments each run, cycles back to min after reaching max.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_value": ("INT", {"default": 0, "min": -0xffffffff, "max": 0xffffffff, "tooltip": "Start of integer range"}),
                "max_value": ("INT", {"default": 10, "min": -0xffffffff, "max": 0xffffffff, "tooltip": "End of integer range"}),
                "step_size": ("INT", {"default": 1, "min": 1, "max": 1000,
                    "tooltip": "Increment per iteration"}),
                "auto_increment": ("BOOLEAN", {"default": True, "tooltip": "Advance iteration automatically each run"}),
                "reset": ("BOOLEAN", {"default": False, "tooltip": "Reset internal counter to zero"}),
            },
            "optional": {
                "iteration": ("INT", {"default": 0, "min": 0, "max": 0xffffffff,
                    "tooltip": "Manual iteration (only used when auto_increment is False)"}),
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("value", "iteration")
    FUNCTION = "iterate"
    CATEGORY = "Utility/Iterate"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        if kwargs.get("auto_increment", True):
            return float("nan")
        return ""

    def iterate(self, min_value, max_value, step_size, auto_increment, reset, iteration=0):
        global _int_iterator_counter

        if reset:
            _int_iterator_counter = 0

        if auto_increment:
            current = _int_iterator_counter
            _int_iterator_counter += 1
        else:
            current = iteration

        # Calculate how many steps fit in range
        value_range = max_value - min_value
        num_steps = (value_range // step_size) + 1

        # Cycle through values
        step_index = current % num_steps
        value = min_value + (step_index * step_size)

        return (value, current)


class ExtractJSONFields:
    """Extract specific fields from JSON and format for logging."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_input": ("JSON", {"tooltip": "JSON object or JSON string input"}),
            },
            "optional": {
                "model_key": ("STRING", {"default": "model", "tooltip": "Dot-path to model field"}),
                "content_key": ("STRING", {"default": "choices.0.message.content", "tooltip": "Dot-path to response text"}),
                "include_tokens": ("BOOLEAN", {"default": False, "tooltip": "Also extract token usage"}),
                "tokens_key": ("STRING", {"default": "usage.total_tokens", "tooltip": "Dot-path to token count"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("model", "content", "formatted", "tokens")
    FUNCTION = "extract"
    CATEGORY = "Utility/JSON"

    def extract(self, json_input, model_key="model", content_key="choices.0.message.content",
                include_tokens=False, tokens_key="usage.total_tokens"):
        try:
            # Parse JSON if it's a string
            if isinstance(json_input, str):
                data = json.loads(json_input)
            else:
                data = json_input

            # Extract fields using dot notation
            model = self._get_nested_value(data, model_key, "Unknown Model")
            content = self._get_nested_value(data, content_key, "No content")
            tokens = self._get_nested_value(data, tokens_key, 0) if include_tokens else 0

            # Format for logging
            formatted = f"Model: {model}\nResponse: {content}"
            if include_tokens:
                formatted += f"\nTokens: {tokens}"

            return (str(model), str(content), formatted, int(tokens) if tokens else 0)

        except Exception as e:
            error_msg = f"Error parsing JSON: {str(e)}"
            return ("Error", error_msg, error_msg, 0)

    def _get_nested_value(self, data, key_path, default=None):
        """Navigate nested dict using dot notation or array indices."""
        try:
            keys = key_path.split(".")
            value = data

            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                elif isinstance(value, list):
                    try:
                        index = int(key)
                        value = value[index]
                    except (ValueError, IndexError):
                        return default
                else:
                    return default

                if value is None:
                    return default

            return value if value is not None else default
        except:
            return default


class FormatJSONForFile:
    """Format JSON data nicely for appending to a file."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("STRING", {"tooltip": "Model name to include in output"}),
                "content": ("STRING", {"tooltip": "Response text to include"}),
            },
            "optional": {
                "tokens": ("INT", {"default": 0, "tooltip": "Token count for this response"}),
                "separator": ("STRING", {"default": "---", "tooltip": "Section divider text"}),
                "include_tokens": ("BOOLEAN", {"default": False, "tooltip": "Include token line in output"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("formatted_text",)
    FUNCTION = "format"
    CATEGORY = "Utility/JSON"


class StringToInt:
    """Convert string to int with fallback."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("STRING", {"default": "", "tooltip": "String to parse as integer"}),
            },
            "optional": {
                "default": ("INT", {"default": 0, "tooltip": "Fallback if parsing fails"}),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("int",)
    FUNCTION = "convert"
    CATEGORY = "Utility/Convert"

    def convert(self, value, default=0):
        try:
            return (int(value.strip()),)
        except Exception:
            return (default,)


class StringToFloat:
    """Convert string to float with fallback."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("STRING", {"default": "", "tooltip": "String to parse as float"}),
            },
            "optional": {
                "default": ("FLOAT", {"default": 0.0, "tooltip": "Fallback if parsing fails"}),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("float",)
    FUNCTION = "convert"
    CATEGORY = "Utility/Convert"

    def convert(self, value, default=0.0):
        try:
            return (float(value.strip()),)
        except Exception:
            return (default,)


class BoolToString:
    """Convert boolean to string with optional labels."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("BOOLEAN", {"default": False, "tooltip": "Boolean input value"}),
            },
            "optional": {
                "true_text": ("STRING", {"default": "true", "tooltip": "Output text when value is true"}),
                "false_text": ("STRING", {"default": "false", "tooltip": "Output text when value is false"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "convert"
    CATEGORY = "Utility/Convert"

    def convert(self, value, true_text="true", false_text="false"):
        return (true_text if value else false_text,)


_picker_counters = {}
# Shuffle order per slot
_picker_shuffles = {}


class StringListPicker:
    """Pick a line from multiline text with random or ordered modes."""

    def __init__(self):
        self._auto_slot = secrets.token_hex(8)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lines_text": ("STRING", {"multiline": True, "default": "", "tooltip": "One candidate value per line"}),
                "mode": (["random_secure", "shuffle_no_repeat", "round_robin", "even_index", "odd_index", "first", "last"], {
                    "default": "shuffle_no_repeat",
                    "tooltip": "random_secure: CSPRNG pick each run (Python secrets); shuffle_no_repeat: shuffled cycle without repeats; round_robin: deterministic order; even_index/odd_index: random pick from matching parity; first/last: fixed pick"
                }),
            },
            "optional": {
                "slot": ("STRING", {"default": "", "tooltip": "State key to share rotation across nodes"}),
                "reset": ("BOOLEAN", {"default": False, "tooltip": "Reset slot counter and shuffle state"}),
                "strip_empty": ("BOOLEAN", {"default": True, "tooltip": "Trim lines and drop blank entries"}),
            }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("value", "index")
    FUNCTION = "pick"
    CATEGORY = "Utility/Strings"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    def pick(self, lines_text, mode="random_secure", slot="", reset=False, strip_empty=True):
        lines = []
        for ln in lines_text.splitlines():
            if strip_empty:
                ln = ln.strip()
                if not ln:
                    continue
            lines.append(ln)

        if not lines:
            return ("", -1)

        key = slot or getattr(self, "_auto_slot", None) or secrets.token_hex(8)
        if not slot and not hasattr(self, "_auto_slot"):
            self._auto_slot = key
        if reset and key in _picker_counters:
            _picker_counters[key] = 0
        if reset:
            _picker_shuffles.pop(key, None)

        if mode == "first":
            idx = 0
        elif mode == "last":
            idx = len(lines) - 1
        elif mode == "even_index":
            even = [i for i in range(len(lines)) if i % 2 == 0]
            if not even:
                return ("", -1)
            idx = secrets.choice(even)
        elif mode == "odd_index":
            odd = [i for i in range(len(lines)) if i % 2 == 1]
            if not odd:
                return ("", -1)
            idx = secrets.choice(odd)
        elif mode == "shuffle_no_repeat":
            entry = _picker_shuffles.get(key)
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
                _picker_shuffles[key] = entry
            idx = entry["order"][entry["pos"]]
            entry["pos"] += 1
        elif mode == "round_robin":
            current = _picker_counters.get(key, 0)
            idx = current % len(lines)
            _picker_counters[key] = current + 1
        else:
            idx = secrets.randbelow(len(lines))

        return (lines[idx], int(idx))

    def format(self, model, content, tokens=0, separator="---", include_tokens=False):
        output = f"Model: {model}\nResponse: {content}"
        if include_tokens and tokens > 0:
            output += f"\nTokens: {tokens}"
        output += f"\n\n{separator}\n\n"
        return (output,)


class HexToInt:
    """Convert a hexadecimal string to an integer."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "hex_string": ("STRING", {"default": "", "tooltip": "Hex string like ff or 0xff"}),
            },
        }

    RETURN_TYPES = ("INT", "STRING")
    RETURN_NAMES = ("value", "decimal_string")
    FUNCTION = "convert"
    CATEGORY = "Utility/Convert"

    def convert(self, hex_string):
        cleaned = hex_string.strip().removeprefix("0x").removeprefix("0X")
        value = int(cleaned, 16) if cleaned else 0
        return (value, str(value))


class IntToHex:
    """Convert an integer to a hexadecimal string."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("INT", {
                    "default": 0,
                    "min": -0xffffffffffffffff,
                    "max": 0xffffffffffffffff,
                    "tooltip": "Integer to convert to hex"
                }),
            },
            "optional": {
                "uppercase": ("BOOLEAN", {"default": False, "tooltip": "Use uppercase hex letters"}),
                "prefix_0x": ("BOOLEAN", {"default": False, "tooltip": "Prefix output with 0x"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("hex_string",)
    FUNCTION = "convert"
    CATEGORY = "Utility/Convert"

    def convert(self, value, uppercase=False, prefix_0x=False):
        hex_out = format(value, "X" if uppercase else "x")
        if prefix_0x:
            hex_out = "0x" + hex_out
        return (hex_out,)


class BypassSwitch:
    """Route bypass or active value."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bypass": ("BOOLEAN", {"default": False, "tooltip": "True routes bypass_value to output"}),
                "bypass_value": ("*", {"tooltip": "Value returned when bypass is true"}),
                "active_value": ("*", {"tooltip": "Value returned when bypass is false"}),
            }
        }

    RETURN_TYPES = ("*", "BOOLEAN")
    RETURN_NAMES = ("output", "is_bypassed")
    FUNCTION = "route"
    CATEGORY = "Utility/Control"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def route(self, bypass, bypass_value, active_value):
        return (bypass_value if bypass else active_value, bool(bypass))


# Node registration
NODE_CLASS_MAPPINGS = {
    "RubyIntToString": IntToString,
    "RubyFloatToString": FloatToString,
    "RubyStringConcat3": StringConcat3,
    "RubyStringConcat4": StringConcat4,
    "RubyStringConcat6": StringConcat6,
    "RubyMixedConcat4": MixedConcat4,
    "RubyIterateFloat": IterateFloat,
    "RubyIterateInt": IterateInt,
    "RubyExtractJSON": ExtractJSONFields,
    "RubyFormatJSON": FormatJSONForFile,
    "RubyStringToInt": StringToInt,
    "RubyStringToFloat": StringToFloat,
    "RubyBoolToString": BoolToString,
    "RubyStringListPicker": StringListPicker,
    "RubyHexToInt": HexToInt,
    "RubyIntToHex": IntToHex,
    "RubyBypassSwitch": BypassSwitch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyIntToString": "Integer to String",
    "RubyFloatToString": "Float to String",
    "RubyStringConcat3": "String Concatenate (3)",
    "RubyStringConcat4": "String Concatenate (4)",
    "RubyStringConcat6": "String Concatenate (6)",
    "RubyMixedConcat4": "Mixed Concatenate (4)",
    "RubyIterateFloat": "Iterate Float",
    "RubyIterateInt": "Iterate Integer",
    "RubyExtractJSON": "Extract JSON Field",
    "RubyFormatJSON": "Format JSON Utility",
    "RubyStringToInt": "String to Integer",
    "RubyStringToFloat": "String to Float",
    "RubyBoolToString": "Boolean to String",
    "RubyStringListPicker": "Random String From List",
    "RubyHexToInt": "Hex to Integer",
    "RubyIntToHex": "Integer to Hex",
    "RubyBypassSwitch": "Bypass Switch",
}
