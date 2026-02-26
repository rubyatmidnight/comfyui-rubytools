"""
SHA256 and HMAC cryptographic utility nodes.
"""
import hashlib
import hmac
import base64


class SHA256Hash:
    """Compute SHA-256 hash of a text string."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "encoding": ("STRING", {"default": "utf-8"}),
                "uppercase": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("hex_digest", "base64_digest")
    FUNCTION = "hash"
    CATEGORY = "Ruby's Nodes/Crypto"

    def hash(self, text, encoding="utf-8", uppercase=False):
        data = (text or "").encode(encoding)
        digest = hashlib.sha256(data).digest()
        hex_out = digest.hex()
        b64_out = base64.b64encode(digest).decode("ascii")
        if uppercase:
            hex_out = hex_out.upper()
        return (hex_out, b64_out)


class HMACSign:
    """Compute HMAC signature of a message with a secret key."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "message": ("STRING", {"multiline": True, "default": ""}),
                "key": ("STRING", {"default": ""}),
            },
            "optional": {
                "algorithm": (["sha256", "sha512", "sha1", "md5"], {"default": "sha256"}),
                "encoding": ("STRING", {"default": "utf-8"}),
                "uppercase": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("hex_digest", "base64_digest")
    FUNCTION = "sign"
    CATEGORY = "Ruby's Nodes/Crypto"

    def sign(self, message, key, algorithm="sha256", encoding="utf-8", uppercase=False):
        key_bytes = (key or "").encode(encoding)
        msg_bytes = (message or "").encode(encoding)
        h = hmac.new(key_bytes, msg_bytes, getattr(hashlib, algorithm))
        digest = h.digest()
        hex_out = digest.hex()
        b64_out = base64.b64encode(digest).decode("ascii")
        if uppercase:
            hex_out = hex_out.upper()
        return (hex_out, b64_out)


NODE_CLASS_MAPPINGS = {
    "RubySHA256Hash": SHA256Hash,
    "RubyHMACSign": HMACSign,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubySHA256Hash": "Hash: SHA-256",
    "RubyHMACSign": "Hash: HMAC",
}
