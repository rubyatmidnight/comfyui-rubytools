"""
Upscale model loader and image upscaler nodes.

Mirrors ComfyUI's built-in nodes_upscale_model.py with current APIs, so they
keep working independently of third-party packs.
"""
import torch

import comfy.utils
import folder_paths
from comfy import model_management

try:
    from spandrel import ModelLoader, ImageModelDescriptor
    _USE_SPANDREL = True
except ImportError:
    _USE_SPANDREL = False
    from comfy_extras.chainner_models import model_loading


class UpscaleModelLoader:
    """Load an upscale model from models/upscale_models/."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_name": (folder_paths.get_filename_list("upscale_models"), {
                    "tooltip": "Upscale model file to load"
                }),
            }
        }

    RETURN_TYPES = ("UPSCALE_MODEL",)
    RETURN_NAMES = ("upscale_model",)
    FUNCTION = "load_model"
    CATEGORY = "Ruby's Nodes/Upscale"

    def load_model(self, model_name):
        model_path = folder_paths.get_full_path("upscale_models", model_name)
        sd = comfy.utils.load_torch_file(model_path, safe_load=True)
        if "module.layers.0.residual_group.blocks.0.norm1.weight" in sd:
            sd = comfy.utils.state_dict_prefix_replace(sd, {"module.": ""})

        if _USE_SPANDREL:
            out = ModelLoader().load_from_state_dict(sd).eval()
            if not isinstance(out, ImageModelDescriptor):
                raise Exception("Upscale model must be a single-image model.")
        else:
            out = model_loading.load_state_dict(sd).eval()

        return (out,)


class ImageUpscaleWithModel:
    """Upscale an image using a loaded upscale model with tiled inference."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "upscale_model": ("UPSCALE_MODEL", {"tooltip": "Loaded upscale model"}),
                "image": ("IMAGE", {"tooltip": "Image batch to upscale"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "upscale"
    CATEGORY = "Ruby's Nodes/Upscale"

    def upscale(self, upscale_model, image):
        device = model_management.get_torch_device()

        memory_required = model_management.module_size(upscale_model.model)
        memory_required += (512 * 512 * 3) * image.element_size() * max(upscale_model.scale, 1.0) * 384.0
        memory_required += image.nelement() * image.element_size()
        model_management.free_memory(memory_required, device)

        upscale_model.to(device)
        in_img = image.movedim(-1, -3).to(device)

        tile = 512
        overlap = 32

        oom = True
        while oom:
            try:
                steps = in_img.shape[0] * comfy.utils.get_tiled_scale_steps(
                    in_img.shape[3], in_img.shape[2],
                    tile_x=tile, tile_y=tile, overlap=overlap,
                )
                pbar = comfy.utils.ProgressBar(steps)
                s = comfy.utils.tiled_scale(
                    in_img,
                    lambda a: upscale_model(a),
                    tile_x=tile, tile_y=tile, overlap=overlap,
                    upscale_amount=upscale_model.scale,
                    pbar=pbar,
                )
                oom = False
            except model_management.OOM_EXCEPTION as e:
                tile //= 2
                if tile < 128:
                    raise e

        upscale_model.to("cpu")
        s = torch.clamp(s.movedim(-3, -1), min=0, max=1.0)
        return (s,)


NODE_CLASS_MAPPINGS = {
    "RubyUpscaleModelLoader": UpscaleModelLoader,
    "RubyImageUpscaleWithModel": ImageUpscaleWithModel,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyUpscaleModelLoader": "Upscale Model Loader",
    "RubyImageUpscaleWithModel": "Image Upscale With Model",
}
