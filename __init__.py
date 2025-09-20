# __init__.py (ComfyUI/custom_nodes/ComfyUI-RadialLengthHelper/__init__.py)

# Let Comfy mount our web assets (for the live overlay JS)
WEB_DIRECTORY = "./web"

from .radial_length_helper import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["WEB_DIRECTORY", "NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
