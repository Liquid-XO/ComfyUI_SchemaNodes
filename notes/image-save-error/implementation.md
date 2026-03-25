# Implementation: Fix Save Functions Pattern Mismatch

**Date**: 2026-03-24  
**Related Investigation**: [investigation.md](./investigation.md)  
**Status**: Implemented

---

## Summary

Fixed three save functions in `schema_nodes.py` to match ComfyUI's native `SaveImage` pattern:

1. `_save_image()` - lines 61-79
2. `_save_video()` - lines 99-137  
3. `_save_text()` - lines 140-152

---

## Changes Made

### 1. `_save_image()` (line 61)

**Before:**
```python
def _save_image(tensor: torch.Tensor, filename_prefix: str) -> list[dict]:
    output_dir = folder_paths.get_output_directory()
    full_output_folder, filename, counter, subfolder, prefix = \
        folder_paths.get_save_image_path(filename_prefix, output_dir)
    # ...
    file = f"{prefix}_{counter + i:05d}.png"
```

**After:**
```python
def _save_image(tensor: torch.Tensor, filename_prefix: str) -> list[dict]:
    output_dir = folder_paths.get_output_directory()
    # Pass image dimensions for template variable support (%width%, %height%)
    h, w = tensor.shape[1], tensor.shape[2]
    full_output_folder, filename, counter, subfolder, prefix = \
        folder_paths.get_save_image_path(filename_prefix, output_dir, w, h)
    # ...
    # Use filename (not prefix) and trailing underscore for counter detection
    file = f"{filename}_{counter + i:05d}_.png"
```

### 2. `_save_video()` (line 99)

**Before:**
```python
def _save_video(tensor, filename_prefix, frame_rate=24.0):
    output_dir = folder_paths.get_output_directory()
    full_output_folder, filename, counter, subfolder, prefix = \
        folder_paths.get_save_image_path(filename_prefix, output_dir)
    file = f"{prefix}_{counter:05d}.mp4"
```

**After:**
```python
def _save_video(tensor, filename_prefix, frame_rate=24.0):
    output_dir = folder_paths.get_output_directory()
    # Pass video dimensions for template variable support (%width%, %height%)
    n, h, w, c = tensor.shape
    full_output_folder, filename, counter, subfolder, prefix = \
        folder_paths.get_save_image_path(filename_prefix, output_dir, w, h)
    # Use filename (not prefix) and trailing underscore for counter detection
    file = f"{filename}_{counter:05d}_.mp4"
```

### 3. `_save_text()` (line 140)

**Before:**
```python
def _save_text(text: str, filename_prefix: str) -> list[dict]:
    output_dir = folder_paths.get_output_directory()
    full_output_folder, filename, counter, subfolder, prefix = \
        folder_paths.get_save_image_path(filename_prefix, output_dir)
    file = f"{prefix}_{counter:05d}.txt"
```

**After:**
```python
def _save_text(text: str, filename_prefix: str) -> list[dict]:
    output_dir = folder_paths.get_output_directory()
    full_output_folder, filename, counter, subfolder, prefix = \
        folder_paths.get_save_image_path(filename_prefix, output_dir)
    # Use filename (not prefix) and trailing underscore for counter detection
    file = f"{filename}_{counter:05d}_.txt"
```

*Note: `_save_text()` doesn't pass dimensions since text has no width/height.*

---

## Bugs Fixed

| Bug | Impact | Fix |
|-----|--------|-----|
| Used `prefix` instead of `filename` | Wrong variable - `prefix` could include path components | Changed to `filename` |
| Missing trailing underscore | Counter detection broken - `get_save_image_path()` couldn't find existing files | Added `_` before extension |
| No dimensions passed | Template variables `%width%`, `%height%` wouldn't work | Pass `w, h` to `get_save_image_path()` |

---

## Testing Required

1. **Image save**: Run workflow with `SchemaImageParameter` in output mode
2. **Counter increment**: Save multiple images, verify counter increments correctly
3. **Video save**: Test `SchemaVideoParameter` output
4. **Text save**: Test `SchemaStringParameter` output mode
5. **Windows**: Verify the OSError is resolved on Windows

---

## Files Modified

- `schema_nodes.py` - lines 61-152 (three functions)
