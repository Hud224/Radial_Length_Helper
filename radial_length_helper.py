"""
ComfyUI Custom Node: Radial Length Helper (WAN)
Compute valid video lengths L for WAN + RadialAttention so that token count is divisible by 128.
Supports WAN 14B (/16) and WAN 5B (/32).

Outputs snapped nearest valid L + inline UI text.
"""

from __future__ import annotations


def _gcd(a: int, b: int) -> int:
    a = abs(int(a)); b = abs(int(b))
    while b:
        a, b = b, a % b
    return a


# =========================
# Radial Length Helper
# =========================
class RadialLengthHelper:
    """Basic helper for WAN RadialAttention.

    Inputs: Model (14B/5B), Width, Height, Length.
    Outputs: Snapped Width, Height, Length.

    Rules:
      - stride = 16 (14B) or 32 (5B)
      - Width/Height snap to nearest multiple of stride
      - Temporal L snaps to nearest valid value satisfying tokens%128 == 0
      - Valid Ls (1..200) are shown in the inline text
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_kind": (["WAN 14B", "WAN 5B"], {"default": "WAN 14B"}),
                "width": ("INT", {"default": 1024, "min": 16, "max": 8192, "step": 16}),
                "height": ("INT", {"default": 576, "min": 16, "max": 8192, "step": 16}),
                "length": ("INT", {"default": 61, "min": 1, "max": 2000, "step": 1}),
            },
        }

    RETURN_TYPES = ("INT", "INT", "INT")
    RETURN_NAMES = ("L_snapped", "W_out", "H_out")
    FUNCTION = "compute"
    CATEGORY = "RadialAttnHelper / RadialLengthHelper"
    OUTPUT_NODE = True

    def compute(self, model_kind: str, width: int, height: int, length: int):
        stride = 16 if model_kind == "WAN 14B" else 32

        # Snap spatial to nearest multiple of model stride
        def _snap(val: int, base: int) -> int:
            if base <= 0:
                return int(val)
            return int(((int(val) + base // 2) // base) * base)

        W_in, H_in = int(width), int(height)
        width = _snap(W_in, stride)
        height = _snap(H_in, stride)

        # Validate spatial after snapping
        if width <= 0 or height <= 0 or (width % stride != 0) or (height % stride != 0):
            msg = (
                f"Invalid spatial for {model_kind}: must be multiples of /{stride}. "
                f"Got {W_in}x{H_in} → {width}x{height}."
            )
            return {"ui": {"text": "ERROR: " + msg}, "result": (int(length), int(width), int(height))}

        Wx = width // stride
        Hx = height // stride
        A = Wx * Hx

        # Congruence L ≡ r (mod m)
        g = _gcd(128, A)
        m = 4 * (128 // g)
        r = (m - 3) % m

        # Snap L to nearest valid value around requested length
        desired_L = max(1, int(length))
        offset = (desired_L - r) % m
        L_floor = desired_L - offset
        L_ceil = desired_L + ((m - offset) % m)
        L_snap = L_floor if abs(desired_L - L_floor) <= abs(L_ceil - desired_L) else L_ceil
        L_snap = max(1, int(L_snap))

        # Build valid L list between 1..200 (inclusive)
        list_min, list_max = 1, 200
        first = r
        if first < list_min:
            k = (list_min - first + m - 1) // m
            first = first + k * m
        samples = []
        Lval = first
        while Lval <= list_max:
            samples.append(Lval)
            Lval += m

        # UI text
        lines = [
            f"spatial: {W_in}x{H_in} → {width}x{height} (/ {stride})",
            f"L snapped: {L_snap}",
            f"valid L (1..200): {len(samples)} vals",
        ]
        # Wrap in rows of 12 for readability
        if samples:
            row = []
            for i, val in enumerate(samples, 1):
                row.append(str(val))
                if i % 12 == 0:
                    lines.append(", ".join(row))
                    row = []
            if row:
                lines.append(", ".join(row))
        else:
            lines.append("(no valid L in range)")

        ui_text = chr(10).join(lines)
        return {"ui": {"text": ui_text}, "result": (int(L_snap), int(width), int(height))}

# =========================
# WAN Token Inspector
# =========================
class WanTokenInspector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_kind": (["WAN 14B", "WAN 5B"], {"default": "WAN 14B"}),
                "width": ("INT", {"default": 1024, "min": 1, "max": 8192, "step": 1}),
                "height": ("INT", {"default": 576, "min": 1, "max": 8192, "step": 1}),
                "L": ("INT", {"default": 61, "min": 1, "max": 2000, "step": 1}),
            },
            "optional": {
                "ui_preview": (["off", "on"], {"default": "on"}),
                "recalc": ("BOOLEAN", {"default": False, "display": "button"}),
            },
        }

    RETURN_TYPES = ("INT", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("Tprime", "Tokens", "Tokens_mod128", "Valid", "Congruence")
    FUNCTION = "inspect"
    CATEGORY = "RadialAttnHelper / WanTokenInspector"
    OUTPUT_NODE = True

    def inspect(self, model_kind: str, width: int, height: int, L: int, ui_preview: str = "on", recalc: bool = False):
        stride = 16 if model_kind == "WAN 14B" else 32
        if width % stride != 0 or height % stride != 0:
            congr = (
                f"Invalid spatial for {model_kind}: width/height must be multiples of /{stride}. "
                f"Got W={width}, H={height}."
            )
            ui_text = "ERROR: " + congr
            return {"ui": {"text": ui_text}, "result": (0, 0, -1, "false", congr)}

        Wx = width // stride
        Hx = height // stride
        A = Wx * Hx

        # Congruence
        g = _gcd(128, A)
        m = 4 * (128 // g)
        r = (m - 3) % m
        congr = f"L ≡ {r} (mod {m})"

        # Temporal pack
        tprime_num = L + 3
        if (tprime_num % 4) != 0:
            Tprime = tprime_num / 4.0
            ui_text = "(L+3)/4 is not an integer → invalid temporal packing" + chr(10) + f"rule: {congr}"
            return {"ui": {"text": ui_text}, "result": (int(Tprime), 0, -1, "false", congr)}
        Tprime = tprime_num // 4

        tokens = A * Tprime
        mod128 = tokens % 128
        valid = (mod128 == 0)

        ui = {}
        if ui_preview == "on":
            lines = [
                f"A=(W/stride)*(H/stride): {A}",
                f"T'=(L+3)/4: {Tprime}",
                f"tokens: {tokens}",
                f"tokens%128: {mod128}",
                f"valid: {'true' if valid else 'false'}",
                f"rule: {congr}",
            ]
            ui_text = chr(10).join(lines)
            ui = {"text": ui_text}

        return {"ui": ui, "result": (int(Tprime), int(tokens), int(mod128), "true" if valid else "false", congr)}


NODE_CLASS_MAPPINGS = {
    "RadialLengthHelper": RadialLengthHelper,
    "WanTokenInspector": WanTokenInspector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RadialLengthHelper": "WAN Radial Length Helper",
    "WanTokenInspector": "WAN Token Inspector",
}
