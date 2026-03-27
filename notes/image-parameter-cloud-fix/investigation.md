# Investigation: SchemaImageParameter Cloud Storage Fix

**Date**: 2026-03-24  
**Status**: IN PROGRESS  
**Confidence**: HIGH

---

## Problem Statement

`SchemaImageParameter` (and `SchemaVideoParameter`) fail on ComfyCloud because they don't handle the dict format `{filename, subfolder, type}` that ComfyCloud returns from uploads.

Error:
```
FileNotFoundError: [Errno 2] No such file or directory: '/app/comfyui/input/2b64bb...png'
```

---

## Root Cause Analysis

### The Actual Bug

The issue is **NOT** in `_load_image()` — that function already uses `folder_paths.get_annotated_filepath()` which handles both string and dict formats.

The bug is in **`SchemaImageParameter.execute()`** at lines 514-518 in `schema_nodes.py`:

```python
if isinstance(value_in, str):
    image_tensor = _load_image(value_in)
else:
    # Already a tensor (connected from another node)
    image_tensor = value_in
```

**Problem**: When `value_in` is a dict (ComfyCloud format), it falls through to the `else` branch and gets treated as a tensor — it never reaches `_load_image()`.

### Evidence

1. **`schema_nodes.py` line 55**: `_load_image` already uses `folder_paths.get_annotated_filepath(filename)` which handles both formats
2. **`schema_nodes.py` line 514-518**: Only passes strings to `_load_image`, treats everything else as tensor
3. **Same pattern in `SchemaVideoParameter`** at lines 573-577

### Why Standard LoadImage Works

ComfyUI's `LoadImage` node passes the image parameter directly to `folder_paths.get_annotated_filepath()` without type checking — it lets the folder_paths module handle both formats.

---

## Affected Files

| File | Lines | Issue |
|------|-------|-------|
| `schema_nodes.py` | 514-518 | SchemaImageParameter only handles str, not dict |
| `schema_nodes.py` | 573-577 | SchemaVideoParameter same issue |
| `schema_nodes.py` | 53 | `_load_image` type hint says `str` but should accept `str | dict` |
| `schema_nodes.py` | 82 | `_load_video` same type hint issue |

---

## Proposed Fix

### IMPORTANT: `get_annotated_filepath` Does NOT Handle Dicts!

The uploaded doc incorrectly assumed `folder_paths.get_annotated_filepath()` accepts `subfolder` and `type` kwargs. **It does not.**

Actual signature:
```python
def get_annotated_filepath(name: str, default_dir: str | None = None) -> str
```

However, there IS `folder_paths.get_directory_by_type(type_name)` which converts `"input"/"output"/"temp"` to paths.

### The Complete Fix

**1. Update `_load_image()` to handle dict format** (line 53):

```python
def _load_image(filename: str | dict) -> torch.Tensor:
    """Load image from input folder, return [1, H, W, C] float32 tensor.
    
    Args:
        filename: Either a string filename, or dict with {filename, subfolder, type}
    """
    if isinstance(filename, dict):
        # ComfyCloud format: {filename, subfolder, type}
        fname = filename.get("filename", "")
        subfolder = filename.get("subfolder", "")
        file_type = filename.get("type", "input")
        base_dir = folder_paths.get_directory_by_type(file_type)
        if base_dir is None:
            base_dir = folder_paths.get_input_directory()
        image_path = os.path.join(base_dir, subfolder, fname) if subfolder else os.path.join(base_dir, fname)
    else:
        image_path = folder_paths.get_annotated_filepath(filename)
    
    img = Image.open(image_path).convert("RGB")
    img_np = np.array(img, dtype=np.float32) / 255.0
    return torch.from_numpy(img_np).unsqueeze(0)  # [1, H, W, C]
```

**2. Update `_load_video()` with same pattern** (line 82)

**3. Update execute() type checks** to pass dicts through:

```python
# In SchemaImageParameter.execute() (line 514)
if isinstance(value_in, (str, dict)):
    image_tensor = _load_image(value_in)
else:
    # Already a tensor (connected from another node)
    image_tensor = value_in

# Same for SchemaVideoParameter.execute() (line 573)
```

---

## Testing Checklist

- [ ] Local file path (string) still works
- [ ] Dict format `{filename, subfolder, type}` works
- [ ] Tensor passthrough (connected from another node) works
- [ ] ComfyCloud execution works
- [ ] Local ComfyUI execution still works
- [ ] Same tests for SchemaVideoParameter

---

## Impact Assessment

| Area | Impact |
|------|--------|
| **ComfyCloud** | Fixes image/video input for all Schema*Parameter nodes |
| **Local ComfyUI** | No change (backward compatible) |
| **Existing workflows** | No change (string format still works) |
| **API Consumers** | Can now pass dict format |

---

## Checkpoint

✅ Root cause identified with file paths and line numbers  
✅ Fix is minimal (2-4 line changes)  
✅ Confidence: HIGH

**Does this analysis look correct? Should I proceed with implementation?**
