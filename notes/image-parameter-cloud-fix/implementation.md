# Implementation: SchemaImageParameter Cloud Storage Fix

**Date**: 2026-03-24  
**Status**: COMPLETE  
**Related**: [investigation.md](./investigation.md)

---

## Changes Made

### 1. `_load_image()` — lines 53-77

**Before:**
```python
def _load_image(filename: str) -> torch.Tensor:
    """Load image from input folder, return [1, H, W, C] float32 tensor."""
    image_path = folder_paths.get_annotated_filepath(filename)
    img = Image.open(image_path).convert("RGB")
    img_np = np.array(img, dtype=np.float32) / 255.0
    return torch.from_numpy(img_np).unsqueeze(0)
```

**After:**
```python
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
    return torch.from_numpy(img_np).unsqueeze(0)
```

---

### 2. `_load_video()` — lines 100-124

Same pattern as `_load_image()` — added dict handling before calling `cv2.VideoCapture()`.

---

### 3. `SchemaImageParameter.execute()` — line 552

**Before:**
```python
if isinstance(value_in, str):
    image_tensor = _load_image(value_in)
else:
    # Already a tensor (connected from another node)
    image_tensor = value_in
```

**After:**
```python
if isinstance(value_in, (str, dict)):
    # String filename or dict {filename, subfolder, type} (ComfyCloud)
    image_tensor = _load_image(value_in)
else:
    # Already a tensor (connected from another node)
    image_tensor = value_in
```

---

### 4. `SchemaVideoParameter.execute()` — line 611

Same change as SchemaImageParameter.

---

## Testing Checklist

- [ ] Local file path (string) still works
- [ ] Dict format `{filename, subfolder, type}` works  
- [ ] Dict with empty subfolder works
- [ ] Dict with non-empty subfolder works
- [ ] Tensor passthrough (connected from another node) works
- [ ] ComfyCloud execution works
- [ ] Local ComfyUI execution still works
- [ ] Same tests for SchemaVideoParameter

---

## Backward Compatibility

✅ **Fully backward compatible**

- String filenames continue to work exactly as before
- Tensor passthrough continues to work
- Only adds support for dict format (additive change)
