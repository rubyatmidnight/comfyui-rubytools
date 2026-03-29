"""
Token counting and chunk estimation nodes.
"""
import math
import re

try:
    import tiktoken
    _HAS_TIKTOKEN = True
except Exception:
    tiktoken = None
    _HAS_TIKTOKEN = False


def _wordpiece_estimate(text):
    if not text:
        return 0
    parts = re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)
    count = 0
    for part in parts:
        if re.fullmatch(r"\w+", part, flags=re.UNICODE):
            count += max(1, math.ceil(len(part) / 4))
        else:
            count += 1
    return count


def _encoding_for_model(model_or_encoding):
    if not _HAS_TIKTOKEN:
        return (None, "estimate")
    model_name = (model_or_encoding or "").strip()
    if not model_name:
        model_name = "gpt-4o-mini"
    lowered = model_name.lower()
    if lowered in {"o200k_base", "cl100k_base", "p50k_base", "r50k_base"}:
        try:
            enc = tiktoken.get_encoding(lowered)
            return (enc, f"tiktoken:{enc.name}")
        except Exception:
            return (None, "estimate")
    try:
        enc = tiktoken.encoding_for_model(model_name)
        return (enc, f"tiktoken:{enc.name}")
    except Exception:
        fallback = "o200k_base" if any(k in lowered for k in ("gpt-4o", "gpt-4.1", "o1", "o3", "o4")) else "cl100k_base"
        try:
            enc = tiktoken.get_encoding(fallback)
            return (enc, f"tiktoken:{enc.name}")
        except Exception:
            return (None, "estimate")


class GPTTokenCount:
    """Estimate OpenAI-style token count."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "", "tooltip": "Prompt or text to count"}),
            },
            "optional": {
                "model_or_encoding": ("STRING", {"default": "gpt-4o-mini", "tooltip": "Model name or encoding name"}),
                "context_window": ("INT", {"default": 128000, "min": 1, "max": 0x7fffffff, "tooltip": "Context size for usage percent"}),
            },
        }

    RETURN_TYPES = ("INT", "INT", "FLOAT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("tokens", "context_window", "percent_used", "over_limit", "method")
    FUNCTION = "count"
    CATEGORY = "Ruby's Nodes/Utility"

    def count(self, text, model_or_encoding="gpt-4o-mini", context_window=128000):
        payload = text or ""
        enc, method = _encoding_for_model(model_or_encoding)
        if enc is not None:
            tokens = len(enc.encode(payload))
        else:
            tokens = _wordpiece_estimate(payload)
            method = "estimate"
        percent_used = (float(tokens) / float(context_window)) * 100.0
        over_limit = tokens > context_window
        return (tokens, context_window, percent_used, over_limit, method)


class CLIPChunkEstimate:
    """Estimate CLIP prompt chunks."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "", "tooltip": "Prompt text to estimate"}),
            },
            "optional": {
                "payload_tokens_per_chunk": ("INT", {"default": 75, "min": 1, "max": 1024, "tooltip": "Prompt tokens per chunk"}),
            },
        }

    RETURN_TYPES = ("INT", "INT", "INT", "INT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("estimated_tokens", "chunks", "tokens_with_special", "total_payload_capacity", "fits_single_chunk", "method")
    FUNCTION = "estimate"
    CATEGORY = "Ruby's Nodes/Utility"

    def estimate(self, text, payload_tokens_per_chunk=75):
        estimated_tokens = _wordpiece_estimate(text or "")
        chunks = math.ceil(estimated_tokens / payload_tokens_per_chunk) if estimated_tokens > 0 else 0
        tokens_with_special = estimated_tokens + (2 * chunks) if chunks > 0 else 0
        total_payload_capacity = chunks * payload_tokens_per_chunk
        fits_single_chunk = estimated_tokens <= payload_tokens_per_chunk
        return (
            estimated_tokens,
            chunks,
            tokens_with_special,
            total_payload_capacity,
            fits_single_chunk,
            "clip-estimate",
        )


NODE_CLASS_MAPPINGS = {
    "RubyGPTTokenCount": GPTTokenCount,
    "RubyCLIPChunkEstimate": CLIPChunkEstimate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyGPTTokenCount": "GPT Token Count",
    "RubyCLIPChunkEstimate": "CLIP Chunk Estimate",
}
