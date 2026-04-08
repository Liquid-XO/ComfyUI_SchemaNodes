import os

import folder_paths
import numpy as np
import torch
from PIL import Image

ROLE_OPTIONS = ["input", "output"]


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _clean_examples(raw):
    if raw is None:
        return []
    items = []
    for line in str(raw).replace("\r", "\n").split("\n"):
        cleaned = line.strip()
        if cleaned:
            items.append(cleaned)
    return items


def _set_if(schema, key, value):
    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    schema[key] = value


def _numeric_constraints(gt, ge, lt, le, multiple_of):
    constraints = {}
    if gt is not None:
        constraints["exclusiveMinimum"] = gt
    if ge is not None:
        constraints["minimum"] = ge
    if lt is not None:
        constraints["exclusiveMaximum"] = lt
    if le is not None:
        constraints["maximum"] = le
    if multiple_of not in (None, 0, 0.0):
        constraints["multipleOf"] = multiple_of
    return constraints


def _load_image(filename: str | dict) -> torch.Tensor:
    """Load image from input folder, return [1, H, W, C] float32 tensor.
    
    Args:
        filename: Either a string filename, or dict with {filename, subfolder, type}
                  (ComfyCloud format)
    """
    if isinstance(filename, dict):
        # ComfyCloud format: {filename, subfolder, type}
        fname = filename.get("filename", "")
        subfolder = filename.get("subfolder", "")
        file_type = filename.get("type", "input")
        base_dir = folder_paths.get_directory_by_type(file_type)
        if base_dir is None:
            base_dir = folder_paths.get_input_directory()
        if subfolder:
            image_path = os.path.join(base_dir, subfolder, fname)
        else:
            image_path = os.path.join(base_dir, fname)
    else:
        image_path = folder_paths.get_annotated_filepath(filename)
    
    img = Image.open(image_path).convert("RGB")
    img_np = np.array(img, dtype=np.float32) / 255.0
    return torch.from_numpy(img_np).unsqueeze(0)  # [1, H, W, C]


def _save_image(
    tensor: torch.Tensor,
    filename_prefix: str,
    save_format: str = "webp",
    quality: int = 90,
) -> list[dict]:
    """Save [B, H, W, C] tensor to output folder, return file metadata.
    
    Args:
        tensor: Image tensor [B, H, W, C] float32 0-1
        filename_prefix: Prefix for output filename
        save_format: "webp", "png", or "jpg"
        quality: 1-100, applies to webp/jpg (ignored for png)
    """
    output_dir = folder_paths.get_output_directory()
    # Pass image dimensions for template variable support (%width%, %height%)
    h, w = tensor.shape[1], tensor.shape[2]
    full_output_folder, filename, counter, subfolder, prefix = \
        folder_paths.get_save_image_path(filename_prefix, output_dir, w, h)

    # Normalize format
    fmt = save_format.lower().strip()
    if fmt == "jpeg":
        fmt = "jpg"
    ext = fmt if fmt in ("webp", "png", "jpg") else "webp"

    results = []
    for i, img_tensor in enumerate(tensor):
        img_np = (img_tensor.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        img = Image.fromarray(img_np)

        # JPEG doesn't support alpha channel
        if ext == "jpg" and img.mode == "RGBA":
            img = img.convert("RGB")

        # Use filename (not prefix) and trailing underscore for counter detection
        file = f"{filename}_{counter + i:05d}_.{ext}"
        filepath = os.path.join(full_output_folder, file)

        if ext == "png":
            img.save(filepath)
        else:  # webp or jpg
            img.save(filepath, quality=quality)

        results.append({"filename": file, "subfolder": subfolder, "type": "output"})

    return results



def _save_text(text: str, filename_prefix: str) -> list[dict]:
    """Save text string to output folder, return file metadata."""
    output_dir = folder_paths.get_output_directory()
    full_output_folder, filename, counter, subfolder, prefix = \
        folder_paths.get_save_image_path(filename_prefix, output_dir)

    # Use filename (not prefix) and trailing underscore for counter detection
    file = f"{filename}_{counter:05d}_.txt"
    filepath = os.path.join(full_output_folder, file)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    return [{"filename": file, "subfolder": subfolder, "type": "output"}]


class BaseSchemaParameterNode:
    CATEGORY = "inout/schema"
    FUNCTION = "execute"

    json_type = "string"
    python_type = "str"
    default_value = None
    output_type = "STRING"
    type_label = "text"

    @classmethod
    def base_required_inputs(cls):
        return {
            "name": ("STRING", {"default": "parameter_name"}),
            "io_kind": (ROLE_OPTIONS, {"default": "input"}),
            "description": ("STRING", {"default": "", "multiline": True}),
            "required": ("BOOLEAN", {"default": True}),
        }

    @classmethod
    def type_required_inputs(cls):
        return {}

    @classmethod
    def optional_inputs(cls):
        return {
            "value_in": (cls.output_type, {"forceInput": True}),
        }

    @classmethod
    def INPUT_TYPES(cls):
        required = cls.base_required_inputs()
        required.update(cls.type_required_inputs())
        return {
            "required": required,
            "optional": cls.optional_inputs(),
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    RETURN_TYPES = ()
    RETURN_NAMES = ("value",)

    def _resolve_value(self, value_in, fallback):
        return fallback if value_in is None else value_in

    def _field_schema(self, *, name, io_kind, description, required):
        schema = {
            "name": _clean_text(name),
            "io": io_kind,
            "type": self.json_type,
            "python_type": self.python_type,
            "required": bool(required),
            "description": str(description),
            "node_type": self.__class__.__name__,
        }
        return schema

    def execute(self, **kwargs):
        raise NotImplementedError


class SchemaStringParameter(BaseSchemaParameterNode):
    output_type = "STRING"
    json_type = "string"
    python_type = "str"
    default_value = ""
    type_label = "string"
    RETURN_TYPES = ("STRING",)

    @classmethod
    def type_required_inputs(cls):
        return {
            "default": ("STRING", {"default": "", "multiline": True}),
            "multiline": ("BOOLEAN", {"default": False}),
            "placeholder": ("STRING", {"default": ""}),
            "min_length": ("INT", {"default": 0, "min": 0, "max": 65535, "step": 1}),
            "max_length": ("INT", {"default": 0, "min": 0, "max": 65535, "step": 1}),
            "pattern": ("STRING", {"default": ""}),
        }

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        default,
        multiline,
        placeholder,
        min_length,
        max_length,
        pattern,
        value_in=None,
    ):
        value = self._resolve_value(value_in, default)
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        field["default"] = default
        if min_length > 0:
            field["minLength"] = min_length
        if max_length > 0:
            field["maxLength"] = max_length
        _set_if(field, "pattern", pattern)
        field["ui"] = {
            "multiline": bool(multiline),
            "placeholder": placeholder,
        }

        if io_kind == "output":
            # Save text to file when in output mode, using name as filename
            file_info = _save_text(str(value), name)
            field["output_files"] = file_info

        return (value,)


class SchemaIntegerParameter(BaseSchemaParameterNode):
    output_type = "INT"
    json_type = "integer"
    python_type = "int"
    default_value = 0
    type_label = "integer"
    RETURN_TYPES = ("INT",)

    @classmethod
    def type_required_inputs(cls):
        return {
            "default": ("INT", {"default": 0, "min": -2147483648, "max": 2147483647, "step": 1}),
            "ge": ("INT", {"default": -2147483648, "min": -2147483648, "max": 2147483647, "step": 1}),
            "gt": ("INT", {"default": -2147483648, "min": -2147483648, "max": 2147483647, "step": 1}),
            "le": ("INT", {"default": 2147483647, "min": -2147483648, "max": 2147483647, "step": 1}),
            "lt": ("INT", {"default": 2147483647, "min": -2147483648, "max": 2147483647, "step": 1}),
            "multiple_of": ("INT", {"default": 0, "min": 0, "max": 2147483647, "step": 1}),
        }

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        default,
        ge,
        gt,
        le,
        lt,
        multiple_of,
        value_in=None,
    ):
        value = int(self._resolve_value(value_in, default))
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        field["default"] = int(default)
        field.update(
            _numeric_constraints(
                None if gt == -2147483648 else int(gt),
                None if ge == -2147483648 else int(ge),
                None if lt == 2147483647 else int(lt),
                None if le == 2147483647 else int(le),
                int(multiple_of),
            )
        )
        return (value,)


class SchemaFloatParameter(BaseSchemaParameterNode):
    output_type = "FLOAT"
    json_type = "number"
    python_type = "float"
    default_value = 0.0
    type_label = "float"
    RETURN_TYPES = ("FLOAT",)

    @classmethod
    def type_required_inputs(cls):
        return {
            "default": ("FLOAT", {"default": 0.0, "min": -1000000.0, "max": 1000000.0, "step": 0.01}),
            "ge": ("FLOAT", {"default": -1000000.0, "min": -1000000.0, "max": 1000000.0, "step": 0.01}),
            "gt": ("FLOAT", {"default": -1000000.0, "min": -1000000.0, "max": 1000000.0, "step": 0.01}),
            "le": ("FLOAT", {"default": 1000000.0, "min": -1000000.0, "max": 1000000.0, "step": 0.01}),
            "lt": ("FLOAT", {"default": 1000000.0, "min": -1000000.0, "max": 1000000.0, "step": 0.01}),
            "multiple_of": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1000000.0, "step": 0.01}),
            "round_to": ("INT", {"default": 0, "min": 0, "max": 10, "step": 1}),
        }

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        default,
        ge,
        gt,
        le,
        lt,
        multiple_of,
        round_to,
        value_in=None,
    ):
        value = float(self._resolve_value(value_in, default))
        if round_to > 0:
            value = round(value, round_to)
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        field["default"] = float(default)
        field.update(
            _numeric_constraints(
                None if gt == -1000000.0 else float(gt),
                None if ge == -1000000.0 else float(ge),
                None if lt == 1000000.0 else float(lt),
                None if le == 1000000.0 else float(le),
                float(multiple_of),
            )
        )
        if round_to > 0:
            field["precision"] = int(round_to)
        return (value,)


class SchemaBooleanParameter(BaseSchemaParameterNode):
    output_type = "BOOLEAN"
    json_type = "boolean"
    python_type = "bool"
    default_value = False
    type_label = "boolean"
    RETURN_TYPES = ("BOOLEAN",)

    @classmethod
    def type_required_inputs(cls):
        return {
            "default": ("BOOLEAN", {"default": False}),
        }

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        default,
        value_in=None,
    ):
        value = bool(self._resolve_value(value_in, default))
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        field["default"] = bool(default)
        return (value,)


class SchemaEnumParameter(BaseSchemaParameterNode):
    output_type = "STRING"
    json_type = "string"
    python_type = "str"
    default_value = ""
    type_label = "enum"
    RETURN_TYPES = ("STRING",)

    @classmethod
    def type_required_inputs(cls):
        return {
            "options": ("STRING", {"default": "option_a\noption_b", "multiline": True}),
            "default": ("STRING", {"default": "option_a"}),
            "allow_custom_value": ("BOOLEAN", {"default": False}),
        }

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        options,
        default,
        allow_custom_value,
        value_in=None,
    ):
        option_list = _clean_examples(options)
        value = self._resolve_value(value_in, default)
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        field["default"] = str(default)
        field["enum"] = option_list
        if allow_custom_value:
            field["allow_custom_value"] = True
        return (str(value),)


class BaseSchemaMediaParameter(BaseSchemaParameterNode):
    RETURN_TYPES = ()

    @classmethod
    def type_required_inputs(cls):
        return {
            "accepted_formats": ("STRING", {"default": "", "multiline": True}),
            "filename_prefix": ("STRING", {"default": "output"}),
        }

    @classmethod
    def optional_inputs(cls):
        return {
            "value_in": ("*", {"forceInput": True}),  # Accept string or tensor
        }


class SchemaImageParameter(BaseSchemaMediaParameter):
    output_type = "IMAGE"
    json_type = "image"
    python_type = "IMAGE"
    type_label = "image"
    RETURN_TYPES = ("IMAGE",)

    @classmethod
    def type_required_inputs(cls):
        base = super().type_required_inputs()
        base["save_format"] = (["webp", "png", "jpg"], {"default": "webp"})
        base["quality"] = ("INT", {"default": 90, "min": 1, "max": 100})
        return base

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        accepted_formats,
        filename_prefix,
        save_format,
        quality,
        value_in=None,
    ):
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        formats = _clean_examples(accepted_formats)
        if formats:
            field["accepted_formats"] = formats

        if io_kind == "input":
            # Input mode: value_in is filename string -> load to tensor
            if value_in is None:
                raise ValueError(f"Input image '{name}' requires a filename")
            if isinstance(value_in, (str, dict)):
                # String filename or dict {filename, subfolder, type} (ComfyCloud)
                image_tensor = _load_image(value_in)
            else:
                # Already a tensor (connected from another node)
                image_tensor = value_in
            return (image_tensor,)

        else:  # io_kind == "output"
            # Output mode: value_in is tensor -> save to file
            if value_in is None:
                raise ValueError(f"Output image '{name}' requires an image tensor")
            file_info = _save_image(value_in, filename_prefix, save_format, quality)
            field["output_files"] = file_info
            return (value_in,)  # Pass through tensor


class SchemaVideoParameter(BaseSchemaMediaParameter):
    """Schema parameter for video file paths.
    
    Unlike SchemaImageParameter which handles tensor conversion,
    this node simply passes through file path strings. Users should
    wire VHS nodes (LoadVideoPath, VideoCombine) for tensor conversion.
    
    Input mode: value_in is cloud filename from MCP upload
    Output mode: value_in is path from upstream VHS node
    """
    output_type = "STRING"
    json_type = "video"
    python_type = "STRING"
    type_label = "video"
    RETURN_TYPES = ("STRING",)

    def execute(
        self,
        name,
        io_kind,
        description,
        required,
        accepted_formats,
        filename_prefix,
        value_in=None,
    ):
        field = self._field_schema(
            name=name,
            io_kind=io_kind,
            description=description,
            required=required,
        )
        formats = _clean_examples(accepted_formats)
        if formats:
            field["accepted_formats"] = formats

        # Both modes: simple string pass-through
        # Input: value_in is cloud filename from MCP upload (e.g., "video_abc123.mp4")
        # Output: value_in is path from upstream VHS node
        if value_in is None:
            mode = "Input" if io_kind == "input" else "Output"
            raise ValueError(f"{mode} video '{name}' requires a file path")
        return (str(value_in),)


class SchemaAudioParameter(BaseSchemaMediaParameter):
    output_type = "AUDIO"
    json_type = "audio"
    python_type = "AUDIO"
    type_label = "audio"
    RETURN_TYPES = ("AUDIO",)


SCHEMA_CLASS_MAPPINGS = {
    "SchemaAudioParameter": SchemaAudioParameter,
    "SchemaStringParameter": SchemaStringParameter,
    "SchemaIntegerParameter": SchemaIntegerParameter,
    "SchemaFloatParameter": SchemaFloatParameter,
    "SchemaBooleanParameter": SchemaBooleanParameter,
    "SchemaEnumParameter": SchemaEnumParameter,
    "SchemaImageParameter": SchemaImageParameter,
    "SchemaVideoParameter": SchemaVideoParameter,
}

SCHEMA_DISPLAY_NAME_MAPPINGS = {
    "SchemaAudioParameter": "Schema Audio Parameter",
    "SchemaStringParameter": "Schema String Parameter",
    "SchemaIntegerParameter": "Schema Integer Parameter",
    "SchemaFloatParameter": "Schema Float Parameter",
    "SchemaBooleanParameter": "Schema Boolean Parameter",
    "SchemaEnumParameter": "Schema Enum Parameter",
    "SchemaImageParameter": "Schema Image Parameter",
    "SchemaVideoParameter": "Schema Video Parameter",
}
