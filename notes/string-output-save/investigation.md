# Investigation: String Output Save to File

**Date**: 2026-03-24  
**Status**: IMPLEMENTED  
**Confidence**: HIGH

---

## Problem Statement

When `SchemaStringParameter` has `io_kind = "output"`, there's no way to actually get the string output from the workflow. Unlike `SchemaImageParameter` and `SchemaVideoParameter` which save their outputs to files, the String node just returns the value without persisting it.

**Requirement**: Save the string value to a text file in ComfyUI's output folder, named after the variable (similar to how image output works).

---

## Research: How ComfyUI Output Nodes Work

### SaveImage Pattern (from `nodes.py`)

```python
class SaveImage:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        
    OUTPUT_NODE = True  # Marks as output node
    RETURN_TYPES = ()   # No output connections
    
    def save_images(self, images, filename_prefix="ComfyUI", ...):
        full_output_folder, filename, counter, subfolder, prefix = \
            folder_paths.get_save_image_path(filename_prefix, self.output_dir, ...)
        
        # ... save files ...
        
        return {
            "ui": {
                "images": [{"filename": file, "subfolder": subfolder, "type": self.type}]
            }
        }
```

### Key Patterns:
1. **`OUTPUT_NODE = True`** - Tells ComfyUI this is a terminal output node
2. **`RETURN_TYPES = ()`** - No outputs to connect (terminal node)
3. **`folder_paths.get_output_directory()`** - Gets ComfyUI output folder
4. **`folder_paths.get_save_image_path()`** - Handles subfolder creation, counter for unique filenames
5. **Return `{"ui": {...}}`** - Provides metadata for UI display

---

## Current State Analysis

### SchemaImageParameter (output mode) - WORKS
```python
# schema_nodes.py lines 465-475
else:  # io_kind == "output"
    if value_in is None:
        raise ValueError(f"Output image '{name}' requires an image tensor")
    file_info = _save_image(value_in, filename_prefix)
    field["output_files"] = file_info
    return (value_in, field)
```

### SchemaStringParameter (output mode) - MISSING SAVE
```python
# schema_nodes.py lines 218-249
def execute(self, name, io_kind, ..., value_in=None):
    value = self._resolve_value(value_in, default)
    field = self._field_schema(...)
    # ... build field ...
    return (value, field)  # Just returns, no file save!
```

**Problem**: String node doesn't differentiate behavior for `io_kind == "output"`.

---

## Implementation Plan

### 1. Add `_save_text()` Helper Function

Similar to `_save_image()` but for text files:

```python
def _save_text(text: str, filename_prefix: str) -> list[dict]:
    """Save text string to output folder, return file metadata."""
    output_dir = folder_paths.get_output_directory()
    full_output_folder, filename, counter, subfolder, prefix = \
        folder_paths.get_save_image_path(filename_prefix, output_dir)
    
    file = f"{prefix}_{counter:05d}.txt"
    filepath = os.path.join(full_output_folder, file)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    
    return [{"filename": file, "subfolder": subfolder, "type": "output"}]
```

### 2. Modify `SchemaStringParameter`

Add `filename_prefix` input and output-mode file saving:

```python
class SchemaStringParameter(BaseSchemaParameterNode):
    # ... existing class attributes ...
    
    @classmethod
    def type_required_inputs(cls):
        return {
            "default": ("STRING", {"default": "", "multiline": True}),
            "multiline": ("BOOLEAN", {"default": False}),
            "placeholder": ("STRING", {"default": ""}),
            "min_length": ("INT", {"default": 0, "min": 0, "max": 65535, "step": 1}),
            "max_length": ("INT", {"default": 0, "min": 0, "max": 65535, "step": 1}),
            "pattern": ("STRING", {"default": ""}),
            "filename_prefix": ("STRING", {"default": "text_output"}),  # NEW
        }

    def execute(self, ..., filename_prefix, value_in=None):
        value = self._resolve_value(value_in, default)
        field = self._field_schema(...)
        # ... existing field building ...
        
        if io_kind == "output":
            # Save text to file when in output mode
            file_info = _save_text(str(value), filename_prefix)
            field["output_files"] = file_info
        
        return (value, field)
```

### 3. Design Decision: Use Variable Name as Filename

The user wants the file named after the variable. Two options:

**Option A**: Use `name` parameter as filename prefix
```python
file_info = _save_text(str(value), name)  # Uses the schema field name
```

**Option B**: Keep separate `filename_prefix` but default to `name`
```python
prefix = filename_prefix if filename_prefix else name
file_info = _save_text(str(value), prefix)
```

**Recommendation**: Option B - more flexible, allows override but defaults sensibly.

---

## Files to Modify

| File | Changes |
|------|--------|
| `schema_nodes.py` | Add `_save_text()`, modify `SchemaStringParameter.type_required_inputs()` and `execute()` |

---

## Edge Cases

1. **Empty string**: Should still create file (empty file is valid output)
2. **Special characters in name**: `folder_paths.get_save_image_path()` handles sanitization
3. **Very long strings**: No issue, just write to file
4. **Unicode**: Use `encoding="utf-8"` in file write

---

## Checkpoint

**Findings**:
- ComfyUI uses `folder_paths` module for output directory management
- `get_save_image_path()` works for any file type (handles counter, subfolder creation)
- Image/Video schema nodes already implement this pattern
- String node just needs the same treatment

**Confidence**: HIGH - This is a straightforward addition following established patterns.

**Ready for implementation**: Yes, pending your confirmation.

Should I proceed to implementation?
