"""
Denoise + Seed Iterator Node

Iterates through denoise values between a floor and 1.0, then increments seed.
Optionally uses a fixed denoise value and iterates seed every step instead.
Supports auto-increment mode for self-contained iteration.
"""

# Global counter for auto-increment mode (persists across calls)
_iteration_counter = 0

class DenoiseSeedIterator:
    """
    Generates seed and denoise values for iterative generation workflows.

    In variable denoise mode:
    - Cycles through N evenly-spaced denoise values from floor to 1.0
    - Increments seed after completing a full denoise cycle

    In fixed denoise mode:
    - Uses the specified fixed denoise value
    - Increments seed every iteration for maximum variety

    In auto-increment mode:
    - Automatically increments the iteration counter each run
    - Use reset to start over from 0
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "tooltip": "Starting seed value"
                }),
                "denoise_steps": ("INT", {
                    "default": 15,
                    "min": 1,
                    "max": 256,
                    "tooltip": "Number of denoise values to iterate through before incrementing seed"
                }),
                "denoise_floor": ("FLOAT", {
                    "default": 0.6,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "Minimum denoise value (maximum is always 1.0)"
                }),
                "use_fixed_denoise": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Toggle: use fixed denoise (seed iterates every step) or cycle through denoise values"
                }),
                "fixed_denoise": ("FLOAT", {
                    "default": 0.8,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "Fixed denoise value (only used when use_fixed_denoise is True)"
                }),
                "auto_increment": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Automatically increment iteration each run (ignores manual iteration input)"
                }),
                "reset": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Reset the auto-increment counter to 0"
                }),
            },
            "optional": {
                "iteration": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffff,
                    "tooltip": "Manual iteration index (only used when auto_increment is False)"
                }),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT", "INT")
    RETURN_NAMES = ("seed", "denoise", "iteration")
    FUNCTION = "iterate"
    CATEGORY = "Ruby's Nodes/sampling"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Always re-execute when auto_increment is enabled
        if kwargs.get("auto_increment", True):
            return float("nan")
        return ""

    def iterate(self, base_seed, denoise_steps, denoise_floor,
                use_fixed_denoise, fixed_denoise, auto_increment, reset, iteration=0):
        """
        Calculate seed and denoise values for the current iteration.
        """
        global _iteration_counter

        # Handle reset
        if reset:
            _iteration_counter = 0

        # Determine which iteration to use
        if auto_increment:
            current_iteration = _iteration_counter
            _iteration_counter += 1
        else:
            current_iteration = iteration

        if use_fixed_denoise:
            # Fixed denoise mode: iterate seed every step for maximum variety
            seed = base_seed + current_iteration
            denoise = fixed_denoise
        else:
            # Variable denoise mode: cycle through denoise values, then increment seed
            seed = base_seed + (current_iteration // denoise_steps)

            # Calculate current position in denoise cycle
            denoise_index = current_iteration % denoise_steps

            # Calculate evenly-spaced denoise value
            denoise_range = 1.0 - denoise_floor
            if denoise_steps > 1:
                denoise_increment = denoise_range / (denoise_steps - 1)
                denoise = denoise_floor + (denoise_index * denoise_increment)
            else:
                denoise = 1.0

        return (seed, denoise, current_iteration)


# Node registration
NODE_CLASS_MAPPINGS = {
    "RubyDenoiseSeedIterator": DenoiseSeedIterator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyDenoiseSeedIterator": "Denoise + Seed Iterator (Midnight)"
}
