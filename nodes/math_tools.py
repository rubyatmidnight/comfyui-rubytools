"""
Safe math expression nodes.
"""
import ast
import math
import random
import re


def _clamp(value, low, high):
    return max(low, min(high, value))


def _lerp(a, b, t):
    return a + (b - a) * t


def _invlerp(value, low, high):
    if high == low:
        return 0.0
    return (value - low) / (high - low)


def _remap(value, in_low, in_high, out_low, out_high):
    return _lerp(out_low, out_high, _invlerp(value, in_low, in_high))


def _wrap(value, low, high):
    span = high - low
    if span == 0:
        return low
    return low + ((value - low) % span)


def _pingpong(value, length):
    if length == 0:
        return 0.0
    span = 2 * length
    wrapped = value % span
    return length - abs(wrapped - length)


def _rand(*args):
    if len(args) == 0:
        return random.random()
    if len(args) == 2:
        return random.uniform(args[0], args[1])
    raise ValueError("rand expects 0 or 2 args.")


def _randint(low, high):
    low_int = int(math.floor(low))
    high_int = int(math.floor(high))
    if high_int < low_int:
        low_int, high_int = high_int, low_int
    return float(random.randint(low_int, high_int))


def _ifelse(condition, when_true, when_false):
    return when_true if condition else when_false


_SAFE_FUNCTIONS = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "degrees": math.degrees,
    "radians": math.radians,
    "clamp": _clamp,
    "lerp": _lerp,
    "invlerp": _invlerp,
    "remap": _remap,
    "wrap": _wrap,
    "pingpong": _pingpong,
    "rand": _rand,
    "randint": _randint,
    "ifelse": _ifelse,
}

_SAFE_NAMES = {
    "pi": math.pi,
    "math_e": math.e,
    "tau": math.tau,
}

_BINARY_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
}

_UNARY_OPS = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
    ast.Not: lambda a: not a,
}

_COMPARE_OPS = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
}


def _eval_expr(node, variables):
    if isinstance(node, ast.Expression):
        return _eval_expr(node.body, variables)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return bool(node.value)
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Only numbers are allowed.")
    if isinstance(node, ast.Name):
        if node.id in variables:
            return float(variables[node.id])
        if node.id in _SAFE_NAMES:
            return float(_SAFE_NAMES[node.id])
        raise ValueError(f"Unknown name: {node.id}")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BINARY_OPS:
            raise ValueError("Operator is not allowed.")
        left = _eval_expr(node.left, variables)
        right = _eval_expr(node.right, variables)
        return float(_BINARY_OPS[op_type](left, right))
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise ValueError("Unary operator is not allowed.")
        return _UNARY_OPS[op_type](_eval_expr(node.operand, variables))
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            for value_node in node.values:
                value = _eval_expr(value_node, variables)
                if not value:
                    return False
            return True
        if isinstance(node.op, ast.Or):
            for value_node in node.values:
                value = _eval_expr(value_node, variables)
                if value:
                    return True
            return False
        raise ValueError("Boolean operator is not allowed.")
    if isinstance(node, ast.Compare):
        left = _eval_expr(node.left, variables)
        for op, comparator in zip(node.ops, node.comparators):
            op_type = type(op)
            if op_type not in _COMPARE_OPS:
                raise ValueError("Comparison is not allowed.")
            right = _eval_expr(comparator, variables)
            if not _COMPARE_OPS[op_type](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.IfExp):
        return _eval_expr(node.body, variables) if _eval_expr(node.test, variables) else _eval_expr(node.orelse, variables)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are allowed.")
        func = _SAFE_FUNCTIONS.get(node.func.id)
        if func is None:
            raise ValueError(f"Function is not allowed: {node.func.id}")
        args = [_eval_expr(arg, variables) for arg in node.args]
        return func(*args)
    raise ValueError("Expression is not allowed.")


def _evaluate_expression(expression, variables):
    parsed = ast.parse(expression, mode="eval")
    return _eval_expr(parsed, variables)


def _has_random_call(expression):
    return bool(re.search(r"\b(rand|randint)\s*\(", expression or ""))


class MathExpression:
    """Evaluate a safe math expression."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "expression": ("STRING", {
                    "multiline": True,
                    "default": "a + b",
                    "tooltip": "Math expression using a-f, math helpers, and conditionals"
                }),
            },
            "optional": {
                "a": ("FLOAT", {"default": 0.0, "min": -1e12, "max": 1e12, "step": 0.001, "tooltip": "Variable a"}),
                "b": ("FLOAT", {"default": 0.0, "min": -1e12, "max": 1e12, "step": 0.001, "tooltip": "Variable b"}),
                "c": ("FLOAT", {"default": 0.0, "min": -1e12, "max": 1e12, "step": 0.001, "tooltip": "Variable c"}),
                "d": ("FLOAT", {"default": 0.0, "min": -1e12, "max": 1e12, "step": 0.001, "tooltip": "Variable d"}),
                "e_value": ("FLOAT", {"default": 0.0, "min": -1e12, "max": 1e12, "step": 0.001, "tooltip": "Variable e"}),
                "f": ("FLOAT", {"default": 0.0, "min": -1e12, "max": 1e12, "step": 0.001, "tooltip": "Variable f"}),
            },
        }

    RETURN_TYPES = ("FLOAT", "INT", "STRING", "BOOLEAN")
    RETURN_NAMES = ("value", "int_value", "text", "ok")
    FUNCTION = "evaluate"
    CATEGORY = "Ruby's Nodes/Utility"

    @classmethod
    def IS_CHANGED(cls, expression="", **kwargs):
        if _has_random_call(expression):
            return float("nan")
        return ""

    def evaluate(self, expression, a=0.0, b=0.0, c=0.0, d=0.0, e_value=0.0, f=0.0):
        variables = {
            "a": a,
            "b": b,
            "c": c,
            "d": d,
            "e": e_value,
            "f": f,
        }
        try:
            value = float(_evaluate_expression(expression or "0", variables))
            return (value, int(value), str(value), True)
        except Exception as exc:
            return (0.0, 0, f"Error: {exc}", False)


class RandomInt:
    """Generate a random integer between min and max (inclusive)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_value": ("INT", {
                    "default": 0,
                    "min": -0xffffffffffffffff,
                    "max": 0xffffffffffffffff,
                    "tooltip": "Minimum value (inclusive)"
                }),
                "max_value": ("INT", {
                    "default": 100,
                    "min": -0xffffffffffffffff,
                    "max": 0xffffffffffffffff,
                    "tooltip": "Maximum value (inclusive)"
                }),
            },
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("value",)
    FUNCTION = "generate"
    CATEGORY = "Ruby's Nodes/Utility"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def generate(self, min_value, max_value):
        if max_value < min_value:
            min_value, max_value = max_value, min_value
        return (random.randint(min_value, max_value),)


class RandomFloat:
    """Generate a random float between min and max."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_value": ("FLOAT", {
                    "default": 0.0,
                    "min": -1e12,
                    "max": 1e12,
                    "step": 0.001,
                    "tooltip": "Minimum value (inclusive)"
                }),
                "max_value": ("FLOAT", {
                    "default": 1.0,
                    "min": -1e12,
                    "max": 1e12,
                    "step": 0.001,
                    "tooltip": "Maximum value (inclusive)"
                }),
            },
            "optional": {
                "decimals": ("INT", {"default": -1, "min": -1, "max": 10,
                    "tooltip": "Round to this many decimals (-1 = no rounding)"}),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("value",)
    FUNCTION = "generate"
    CATEGORY = "Ruby's Nodes/Utility"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def generate(self, min_value, max_value, decimals=-1):
        if max_value < min_value:
            min_value, max_value = max_value, min_value
        value = random.uniform(min_value, max_value)
        if decimals >= 0:
            value = round(value, decimals)
        return (value,)


class RandomHex:
    """Generate a random hexadecimal string of a given length."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "digits": ("INT", {"default": 8, "min": 1, "max": 256,
                    "tooltip": "Number of hex digits to generate"}),
            },
            "optional": {
                "uppercase": ("BOOLEAN", {"default": False, "tooltip": "Use uppercase hex letters"}),
                "prefix_0x": ("BOOLEAN", {"default": False, "tooltip": "Prefix output with 0x"}),
            },
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("hex_string", "int_value")
    FUNCTION = "generate"
    CATEGORY = "Ruby's Nodes/Utility"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def generate(self, digits, uppercase=False, prefix_0x=False):
        max_value = (1 << (digits * 4)) - 1
        value = random.randint(0, max_value)
        fmt = f"{{:0{digits}{'X' if uppercase else 'x'}}}"
        hex_out = fmt.format(value)
        if prefix_0x:
            hex_out = "0x" + hex_out
        return (hex_out, value)


class RandomRoll:
    """Roll a random float and compare against a threshold. Returns 1 if roll >= threshold, else 0."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "threshold": ("FLOAT", {
                    "default": 0.9,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "Roll must be >= this value to succeed (0.9 = 10% chance)"
                }),
            },
        }

    RETURN_TYPES = ("INT", "BOOLEAN", "FLOAT")
    RETURN_NAMES = ("result", "success", "roll")
    FUNCTION = "roll"
    CATEGORY = "Ruby's Nodes/Utility"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def roll(self, threshold):
        r = random.random()
        success = r >= threshold
        return (1 if success else 0, success, r)


NODE_CLASS_MAPPINGS = {
    "RubyMathExpression": MathExpression,
    "RubyRandomInt": RandomInt,
    "RubyRandomFloat": RandomFloat,
    "RubyRandomHex": RandomHex,
    "RubyRandomRoll": RandomRoll,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyMathExpression": "Math Expression",
    "RubyRandomInt": "Random Integer",
    "RubyRandomFloat": "Random Float",
    "RubyRandomHex": "Random Hex",
    "RubyRandomRoll": "Random Roll",
}
