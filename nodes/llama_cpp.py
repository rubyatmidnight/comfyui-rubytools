"""
llama.cpp integration via a running llama-server (OpenAI-compatible HTTP API).

Start the server separately, e.g.:
    llama-server -m model.gguf --port 8080
Multimodal (vision) needs a projector:
    llama-server -m model.gguf --mmproj mmproj.gguf --port 8080
"""
import base64
import io
import json
import urllib.request
import urllib.error


DEFAULT_URL = "http://127.0.0.1:8080"


def _post_json(server, path, payload):
    url = server["base_url"].rstrip("/") + path
    headers = {"Content-Type": "application/json"}
    if server.get("api_key"):
        headers["Authorization"] = f"Bearer {server['api_key']}"
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=server.get("timeout", 300)) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"llama-server HTTP {e.code} at {url}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Could not reach llama-server at {url} ({e.reason}). Is it running?"
        ) from e


def _chat(server, messages, options):
    payload = {"messages": messages, **options}
    if server.get("model"):
        payload["model"] = server["model"]
    data = _post_json(server, "/v1/chat/completions", payload)
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected llama-server response: {str(data)[:500]}") from e


def _sampling_inputs():
    return {
        "max_tokens": ("INT", {"default": 512, "min": 1, "max": 32768, "tooltip": "Max tokens to generate"}),
        "temperature": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 5.0, "step": 0.05, "tooltip": "Sampling temperature"}),
        "top_p": ("FLOAT", {"default": 0.95, "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "Nucleus sampling"}),
        "top_k": ("INT", {"default": 40, "min": 0, "max": 500, "tooltip": "Top-k sampling, 0 disables"}),
        "min_p": ("FLOAT", {"default": 0.05, "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "Min-p sampling"}),
        "repeat_penalty": ("FLOAT", {"default": 1.1, "min": 0.0, "max": 2.0, "step": 0.01, "tooltip": "Repetition penalty"}),
        "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFF, "tooltip": "Sampling seed; also busts ComfyUI's cache"}),
    }


def _options(max_tokens, temperature, top_p, top_k, min_p, repeat_penalty, seed):
    return {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "min_p": min_p,
        "repeat_penalty": repeat_penalty,
        "seed": seed,
    }


class LlamaServer:
    RETURN_TYPES = ("LLAMA_SERVER",)
    RETURN_NAMES = ("server",)
    FUNCTION = "configure"
    CATEGORY = "Ruby's Nodes/LLM"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_url": ("STRING", {"default": DEFAULT_URL, "tooltip": "llama-server address"}),
            },
            "optional": {
                "api_key": ("STRING", {"default": "", "tooltip": "Bearer token if the server uses --api-key"}),
                "model": ("STRING", {"default": "", "tooltip": "Model name, only needed for multi-model routers"}),
                "timeout": ("INT", {"default": 300, "min": 5, "max": 3600, "tooltip": "Request timeout in seconds"}),
            },
        }

    def configure(self, base_url, api_key="", model="", timeout=300):
        return ({"base_url": base_url, "api_key": api_key, "model": model, "timeout": timeout},)


class LlamaChat:
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "generate"
    CATEGORY = "Ruby's Nodes/LLM"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "server": ("LLAMA_SERVER",),
                "prompt": ("STRING", {"multiline": True, "default": "", "tooltip": "User message"}),
                **_sampling_inputs(),
            },
            "optional": {
                "system_prompt": ("STRING", {"multiline": True, "default": "", "tooltip": "System message; wire a character card here"}),
                "context": ("STRING", {"multiline": True, "default": "", "tooltip": "Extra context (memories, scene) appended to the system message"}),
                "prefill": ("STRING", {"default": "", "tooltip": "Start of the assistant reply, prepended to the output"}),
            },
        }

    def generate(self, server, prompt, max_tokens, temperature, top_p, top_k, min_p,
                 repeat_penalty, seed, system_prompt="", context="", prefill=""):
        system = "\n\n".join(s for s in (system_prompt.strip(), context.strip()) if s)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        if prefill:
            messages.append({"role": "assistant", "content": prefill})
        text = _chat(server, messages, _options(max_tokens, temperature, top_p, top_k,
                                                min_p, repeat_penalty, seed))
        return (prefill + text if prefill else text,)


ENHANCE_SYSTEM = (
    "You expand short image ideas into detailed Stable Diffusion prompts. "
    "Reply with ONLY the prompt: comma-separated tags and short phrases covering subject, "
    "style, lighting, composition, and quality terms. No explanations, no quotes."
)


class LlamaPromptEnhance:
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("enhanced", "original")
    FUNCTION = "enhance"
    CATEGORY = "Ruby's Nodes/LLM"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "server": ("LLAMA_SERVER",),
                "prompt": ("STRING", {"multiline": True, "default": "", "tooltip": "Short image idea to expand"}),
                **_sampling_inputs(),
            },
            "optional": {
                "style_hint": ("STRING", {"default": "", "tooltip": "Style to steer toward, e.g. 'watercolor, soft light'"}),
                "instructions": ("STRING", {"multiline": True, "default": ENHANCE_SYSTEM, "tooltip": "System prompt for the enhancer"}),
            },
        }

    def enhance(self, server, prompt, max_tokens, temperature, top_p, top_k, min_p,
                repeat_penalty, seed, style_hint="", instructions=ENHANCE_SYSTEM):
        user = prompt if not style_hint.strip() else f"{prompt}\n\nStyle: {style_hint.strip()}"
        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": user},
        ]
        text = _chat(server, messages, _options(max_tokens, temperature, top_p, top_k,
                                                min_p, repeat_penalty, seed))
        return (text.strip().strip('"'), prompt)


def _image_to_data_url(image):
    import numpy as np
    from PIL import Image
    arr = (image[0].cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


class LlamaVision:
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "describe"
    CATEGORY = "Ruby's Nodes/LLM"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "server": ("LLAMA_SERVER",),
                "image": ("IMAGE",),
                "prompt": ("STRING", {"multiline": True, "default": "Describe this image in detail.", "tooltip": "Question or instruction about the image"}),
                **_sampling_inputs(),
            },
            "optional": {
                "system_prompt": ("STRING", {"multiline": True, "default": "", "tooltip": "Optional system message"}),
            },
        }

    def describe(self, server, image, prompt, max_tokens, temperature, top_p, top_k,
                 min_p, repeat_penalty, seed, system_prompt=""):
        messages = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": _image_to_data_url(image)}},
            ],
        })
        text = _chat(server, messages, _options(max_tokens, temperature, top_p, top_k,
                                                min_p, repeat_penalty, seed))
        return (text,)


NODE_CLASS_MAPPINGS = {
    "LlamaServer": LlamaServer,
    "LlamaChat": LlamaChat,
    "LlamaPromptEnhance": LlamaPromptEnhance,
    "LlamaVision": LlamaVision,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LlamaServer": "Llama Server (llama.cpp)",
    "LlamaChat": "Llama Chat (llama.cpp)",
    "LlamaPromptEnhance": "Llama Prompt Enhance (llama.cpp)",
    "LlamaVision": "Llama Vision (llama.cpp)",
}
