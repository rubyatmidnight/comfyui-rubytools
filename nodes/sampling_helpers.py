"""
Sampling workflow helpers.

ScoutRefineSwitch:  one-toggle preset bundle for "fast preview" vs "final"
                    sampling. Outputs steps, cfg, lora strength, and denoise
                    so a single switch reconfigures the whole sampler chain.

VAECachedEncode:    image -> latent encoder with content-hashed caching, so
                    a fixed source image isn't re-encoded every iteration in
                    a prompt/seed sweep.
"""
import hashlib
import secrets

import torch


# ----- Scout / Refine switch ------------------------------------------------


class ScoutRefineSwitch:
    """
    Pick between two preset bundles for sampler params:
    - scout:  fast preview pass (e.g. 6 steps, CFG ~1.5, distill LoRA at 1.0)
    - refine: final-quality pass (e.g. 28 steps, CFG ~7, distill LoRA at 0)

    Wire `steps`/`cfg`/`denoise` into your sampler and `lora_strength` into
    the LoRA loader feeding the model. Toggle `mode` to flip the whole chain.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["scout", "refine"], {"default": "scout",
                    "tooltip": "scout = fast exploration; refine = final quality"}),

                "scout_steps": ("INT", {"default": 6, "min": 1, "max": 200,
                    "tooltip": "Sampler steps when mode is scout"}),
                "scout_cfg": ("FLOAT", {"default": 1.5, "min": 0.0, "max": 30.0, "step": 0.1,
                    "tooltip": "CFG when mode is scout (Lightning/Hyper LoRAs usually want ~1-2)"}),
                "scout_lora_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.05,
                    "tooltip": "Distillation LoRA strength when scouting"}),
                "scout_denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01,
                    "tooltip": "Denoise when scouting (1.0 = full t2i)"}),

                "refine_steps": ("INT", {"default": 28, "min": 1, "max": 200,
                    "tooltip": "Sampler steps when mode is refine"}),
                "refine_cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 30.0, "step": 0.1,
                    "tooltip": "CFG when mode is refine"}),
                "refine_lora_strength": ("FLOAT", {"default": 0.0, "min": -10.0, "max": 10.0, "step": 0.05,
                    "tooltip": "Distillation LoRA strength when refining (0 disables it)"}),
                "refine_denoise": ("FLOAT", {"default": 0.55, "min": 0.0, "max": 1.0, "step": 0.01,
                    "tooltip": "Denoise when refining (lower keeps more of source latent)"}),
            },
        }

    RETURN_TYPES = ("INT", "FLOAT", "FLOAT", "FLOAT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("steps", "cfg", "lora_strength", "denoise", "is_refine", "mode")
    FUNCTION = "switch"
    CATEGORY = "Ruby's Nodes/sampling"

    def switch(self, mode,
               scout_steps, scout_cfg, scout_lora_strength, scout_denoise,
               refine_steps, refine_cfg, refine_lora_strength, refine_denoise):
        if mode == "refine":
            return (refine_steps, refine_cfg, refine_lora_strength,
                    refine_denoise, True, mode)
        return (scout_steps, scout_cfg, scout_lora_strength,
                scout_denoise, False, mode)


# ----- VAE encode with content-hashed cache --------------------------------


_vae_cache = {}


def _image_fingerprint(image_tensor):
    """Cheap content hash for a (B, H, W, C) float image tensor.

    Uses shape plus a downsampled byte projection so iterating prompts/seeds
    over a fixed source image always hits the cache without scanning every
    pixel."""
    shape = tuple(image_tensor.shape)
    # Downsample for speed: stride sample on H/W, sum every channel
    sample = image_tensor[..., ::32, ::32, :].contiguous()
    # Quantize to uint8 to remove FP noise across encode runs
    sample_u8 = (sample.clamp(0.0, 1.0) * 255.0).to(torch.uint8)
    digest = hashlib.blake2b(sample_u8.cpu().numpy().tobytes(), digest_size=16).hexdigest()
    return f"{shape}|{digest}"


class VAECachedEncode:
    """
    Encode an image to a latent, caching the result by image content hash.

    Useful when iterating prompts/seeds/cfg/etc. over a fixed source image:
    Comfy's default execution cache can invalidate when sibling inputs
    change, but this node only re-encodes when the image bytes themselves
    actually change (or when force_refresh is true).
    """

    def __init__(self):
        self._auto_slot = secrets.token_hex(8)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pixels": ("IMAGE", {"tooltip": "Source image to encode"}),
                "vae": ("VAE", {"tooltip": "VAE used for encoding"}),
            },
            "optional": {
                "slot": ("STRING", {"default": "",
                    "tooltip": "Shared cache key (leave empty for per-node cache)"}),
                "force_refresh": ("BOOLEAN", {"default": False,
                    "tooltip": "Re-encode even if the image hash matches the cache"}),
            }
        }

    RETURN_TYPES = ("LATENT", "BOOLEAN")
    RETURN_NAMES = ("latent", "cache_hit")
    FUNCTION = "encode"
    CATEGORY = "Ruby's Nodes/sampling"

    @classmethod
    def IS_CHANGED(cls, pixels, vae, slot="", force_refresh=False, **kwargs):
        # Re-evaluate when force_refresh is on; otherwise stable per image content.
        if force_refresh:
            return float("nan")
        try:
            return _image_fingerprint(pixels) + "|" + str(id(vae))
        except Exception:
            return float("nan")

    def encode(self, pixels, vae, slot="", force_refresh=False):
        key = slot or self._auto_slot
        fp = _image_fingerprint(pixels)
        vae_key = id(vae)

        cached = _vae_cache.get(key)
        if (not force_refresh
                and cached
                and cached["fp"] == fp
                and cached["vae_key"] == vae_key):
            return ({"samples": cached["latent"]}, True)

        # Strip alpha if present, match Comfy's convention
        if pixels.shape[-1] == 4:
            pixels = pixels[..., :3]

        latent = vae.encode(pixels)
        _vae_cache[key] = {"fp": fp, "vae_key": vae_key, "latent": latent}
        return ({"samples": latent}, False)


NODE_CLASS_MAPPINGS = {
    "RubyScoutRefineSwitch": ScoutRefineSwitch,
    "RubyVAECachedEncode": VAECachedEncode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyScoutRefineSwitch": "Scout / Refine Switch",
    "RubyVAECachedEncode": "VAE Encode (cached)",
}
