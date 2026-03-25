# Investigation: Image Save Error (OSError Invalid Argument)

**Date**: 2026-03-24  
**Status**: IN PROGRESS  
**Confidence**: LOW (initial investigation)

---

## Problem Statement

When running `[OUT] Schema Image Parameter` node, an error occurs:

```
OSError: [Errno 22] Invalid argument: 'C:\\Users\\dumbass\\ComfyUI\\output\\style_taxonomy_00001.png'
```

The error occurs at:
- `schema_nodes.py`, line 73 in `_save_image()`
- `img.save(os.path.join(full_output_folder, file))`

---

## Initial Observations

### 1. Error Type Analysis

`OSError: [Errno 22] Invalid argument` on Windows typically means:
- **Invalid filename characters** (e.g., `<`, `>`, `:`, `"`, `/`, `\`, `|`, `?`, `*`)
- **Reserved filenames** (e.g., `CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`)
- **Path too long** (>260 chars on older Windows)
- **File already open by another process**
- **Invalid timestamp/metadata** in image being saved

### 2. Filename in Error

The filename `style_taxonomy_00001.png` appears valid:
- No invalid characters visible
- Not a reserved name
- Path length seems reasonable

### 3. Current Code Flow

```python
def _save_image(tensor: torch.Tensor, filename_prefix: str) -> list[dict]:
    output_dir = folder_paths.get_output_directory()
    full_output_folder, filename, counter, subfolder, prefix = \
        folder_paths.get_save_image_path(filename_prefix, output_dir)

    results = []
    for i, img_tensor in enumerate(tensor):
        img_np = (img_tensor.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        img = Image.fromarray(img_np)

        file = f"{prefix}_{counter + i:05d}.png"
        img.save(os.path.join(full_output_folder, file))
        results.append({"filename": file, "subfolder": subfolder, "type": "output"})

    return results
```

---

## Hypotheses

### H1: `filename_prefix` Contains Invalid Characters (HIGH LIKELIHOOD)

The `filename_prefix` comes from user input (`name` field in the node). If user enters something like:
- `style/taxonomy` → creates invalid path on Windows
- `style:taxonomy` → colon is invalid on Windows
- `style taxonomy` → spaces might cause issues in some contexts

**Evidence needed**: Check what characters are in `style_taxonomy` - the underscore suggests it might have been sanitized already, OR the user entered it that way.

### H2: Counter Not Incrementing Properly (MEDIUM LIKELIHOOD)

User mentioned: "images are not really checking if there are other images with same name and incrementing the number after them like comfyui normally does"

This suggests `get_save_image_path` might not be working as expected, OR we're not using its return values correctly.

**Evidence needed**: Compare our usage with ComfyUI's native SaveImage node.

### H3: Tensor Data Issue (LOW LIKELIHOOD)

The tensor might have invalid data that PIL can't save:
- Wrong shape
- Wrong dtype
- NaN or Inf values

**Evidence needed**: The error message points to file open, not image encoding.

### H4: File Permission/Lock Issue (LOW LIKELIHOOD)

File might be locked by another process or permission denied.

**Evidence needed**: Error is "Invalid argument", not "Permission denied".

---

## Investigation Plan

1. **Research ComfyUI's SaveImage implementation** - How does it sanitize filenames?
2. **Check `get_save_image_path` behavior** - What does it return? Does it sanitize?
3. **Look for filename sanitization in ComfyUI** - Is there a utility function?
4. **Test hypothesis H1** - Check if `style_taxonomy` had special chars before

---

## Research Findings

### ComfyUI's `get_save_image_path` Implementation

From `folder_paths.py`:

```python
def get_save_image_path(filename_prefix: str, output_dir: str, image_width=0, image_height=0) -> tuple[str, str, int, str, str]:
    def map_filename(filename: str) -> tuple[int, str]:
        prefix_len = len(os.path.basename(filename_prefix))
        prefix = filename[:prefix_len + 1]
        try:
            digits = int(filename[prefix_len + 1:].split('_')[0])
        except:
            digits = 0
        return digits, prefix

    # ... compute_vars for %width%, %date%, etc ...

    subfolder = os.path.dirname(os.path.normpath(filename_prefix))
    filename = os.path.basename(os.path.normpath(filename_prefix))

    full_output_folder = os.path.join(output_dir, subfolder)

    # Security check - prevent saving outside output folder
    if os.path.commonpath((output_dir, os.path.abspath(full_output_folder))) != output_dir:
        raise Exception("Saving image outside the output folder is not allowed.")

    try:
        counter = max(filter(lambda a: os.path.normcase(a[1][:-1]) == os.path.normcase(filename) and a[1][-1] == "_", 
                             map(map_filename, os.listdir(full_output_folder))))[0] + 1
    except ValueError:
        counter = 1
    except FileNotFoundError:
        os.makedirs(full_output_folder, exist_ok=True)
        counter = 1
    return full_output_folder, filename, counter, subfolder, filename_prefix
```

**Key observation**: `get_save_image_path` returns:
- `full_output_folder`: The directory path
- `filename`: The base filename (WITHOUT extension, WITHOUT counter)
- `counter`: The next available counter
- `subfolder`: Subfolder relative to output_dir
- `filename_prefix`: The original prefix

### ComfyUI's Native SaveImage Implementation

```python
class SaveImage:
    def save_images(self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None):
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = \
            folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        
        results = list()
        for (batch_number, image) in enumerate(images):
            # ... image processing ...
            
            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            file = f"{filename_with_batch_num}_{counter:05}_.png"  # <-- NOTE THE TRAILING UNDERSCORE!
            img.save(os.path.join(full_output_folder, file), ...)
            counter += 1  # <-- INCREMENTS COUNTER FOR EACH IMAGE IN BATCH!
```

### Our Current Implementation

```python
def _save_image(tensor: torch.Tensor, filename_prefix: str) -> list[dict]:
    output_dir = folder_paths.get_output_directory()
    full_output_folder, filename, counter, subfolder, prefix = \
        folder_paths.get_save_image_path(filename_prefix, output_dir)

    results = []
    for i, img_tensor in enumerate(tensor):
        # ...
        file = f"{prefix}_{counter + i:05d}.png"  # <-- WRONG! Using prefix instead of filename
        img.save(os.path.join(full_output_folder, file))
```

---

## ROOT CAUSE IDENTIFIED

### Issue 1: Using `prefix` instead of `filename`

Our code uses `prefix` (which is the full `filename_prefix` including any subfolder path) instead of `filename` (which is just the base name).

**Example:**
- If `filename_prefix = "style_taxonomy"`
- `get_save_image_path` returns:
  - `filename = "style_taxonomy"` (correct base name)
  - `prefix = "style_taxonomy"` (same in this case, but could differ with subfolders)

This might not be the direct cause but is inconsistent with ComfyUI's pattern.

### Issue 2: Missing trailing underscore in filename pattern

ComfyUI uses: `f"{filename}_{counter:05}_.png"` (note trailing underscore before extension)
Our code uses: `f"{prefix}_{counter + i:05d}.png"` (no trailing underscore)

This affects the counter detection logic in `get_save_image_path`:
```python
# ComfyUI's map_filename looks for pattern: {filename}_{counter}_
filter(lambda a: ... and a[1][-1] == "_", ...)  # Expects underscore before digits!
```

### Issue 3: Potential Windows Path Issues

The error `OSError: [Errno 22] Invalid argument` on Windows could be caused by:
1. **Colons in filename** - If `filename_prefix` contains special template variables like `%date:yyyy-MM-dd%`, the colon could cause issues
2. **Path normalization** - Windows path handling differences

### Issue 4: Not passing image dimensions to `get_save_image_path`

ComfyUI passes `images[0].shape[1], images[0].shape[0]` (width, height) for template variable substitution.
Our code doesn't pass these, which could cause issues if user uses `%width%` or `%height%` in filename.

---

## CONFIRMED ROOT CAUSE

Looking at the error path: `style_taxonomy_00001.png`

The filename looks valid. The most likely cause is:

**The `name` field from the node might contain characters that are valid in the UI but invalid on Windows filesystem.**

Possible hidden characters or encoding issues:
- Zero-width characters
- Unicode characters that look like ASCII but aren't
- Newlines or other control characters

OR:

**The tensor data might be problematic** - but this is unlikely since the error is at file open, not image encoding.

---

## Comparison: Our Code vs ComfyUI

| Aspect | ComfyUI SaveImage | Our _save_image |
|--------|-------------------|------------------|
| Uses `filename` from get_save_image_path | ✅ Yes | ❌ No, uses `prefix` |
| Trailing underscore in pattern | ✅ `_{counter:05}_.png` | ❌ `_{counter:05d}.png` |
| Passes image dimensions | ✅ Yes | ❌ No |
| Increments counter per batch image | ✅ Yes | ✅ Yes (via `counter + i`) |
| Creates output folder | ✅ Via get_save_image_path | ✅ Via get_save_image_path |

---

## Recommended Fixes

1. **Use `filename` instead of `prefix`** for building the output filename
2. **Add trailing underscore** to match ComfyUI's pattern: `f"{filename}_{counter:05}_.png"`
3. **Pass image dimensions** to `get_save_image_path`
4. **Consider sanitizing `filename_prefix`** to remove invalid Windows characters

---

## Additional Finding: Workflow Analysis

Checked `helios/workflows/style.json` for the `style_taxonomy` node:

```json
"widgets_values": [
    "style_taxonomy",              // name
    "output",                       // io_kind
    "the style taxonomy image\n",  // description - HAS NEWLINE!
    true,                           // required
    "",                             // accepted_formats (empty)
    "style_taxonomy"                // filename_prefix
]
```

**Key observation**: The `description` field contains a trailing newline `\n`. While this isn't directly used in the filename, it shows the workflow has some whitespace artifacts.

The `filename_prefix` is `"style_taxonomy"` which looks clean.

---

## CONFIRMED ROOT CAUSES

### Issue 1: Wrong Variable Used (DEFINITE BUG)
```python
# Our code (line 72):
file = f"{prefix}_{counter + i:05d}.png"

# Should be:
file = f"{filename}_{counter + i:05d}_.png"
```

`prefix` is the full `filename_prefix` (which could include path components), while `filename` is the sanitized base name from `get_save_image_path()`.

### Issue 2: Missing Trailing Underscore (DEFINITE BUG)
ComfyUI's pattern: `{filename}_{counter:05}_.png`
Our pattern: `{prefix}_{counter:05d}.png`

The trailing underscore is **critical** for counter detection in `get_save_image_path()`.

### Issue 3: Not Passing Image Dimensions (MINOR)
ComfyUI passes dimensions for template variable support. Our code doesn't.

### Issue 4: Windows OSError (NEEDS MORE INVESTIGATION)
The error `OSError: [Errno 22] Invalid argument` on Windows with path:
`C:\Users\dumbass\ComfyUI\output\style_taxonomy_00001.png`

Possible causes:
1. **Antivirus/security software** blocking file creation
2. **File system permissions** issue
3. **Tensor data issue** causing PIL to fail (less likely since error is at file open)
4. **Hidden characters** in prefix (unlikely based on workflow analysis)

---

## RECOMMENDED FIXES

### Fix 1: Correct `_save_image()` function

```python
def _save_image(tensor: torch.Tensor, filename_prefix: str) -> list[dict]:
    """Save [B, H, W, C] tensor to output folder, return file metadata."""
    output_dir = folder_paths.get_output_directory()
    
    # Pass image dimensions for template variable support
    h, w = tensor.shape[1], tensor.shape[2]
    full_output_folder, filename, counter, subfolder, prefix = \
        folder_paths.get_save_image_path(filename_prefix, output_dir, w, h)

    results = []
    for i, img_tensor in enumerate(tensor):
        img_np = (img_tensor.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        img = Image.fromarray(img_np)

        # Use filename (not prefix) and add trailing underscore for counter detection
        file = f"{filename}_{counter + i:05d}_.png"
        img.save(os.path.join(full_output_folder, file))
        results.append({"filename": file, "subfolder": subfolder, "type": "output"})

    return results
```

### Fix 2: Apply same pattern to `_save_video()` and `_save_text()`

These functions have the same bugs.

---

## Confidence Level: HIGH

The pattern mismatch is definitively a bug based on ComfyUI source code comparison. The fixes are straightforward.

The Windows OSError may or may not be related - it could be:
- A side effect of the wrong filename pattern
- An environmental issue on that specific Windows machine
- Resolved by using the correct `filename` variable instead of `prefix`

---

## CHECKPOINT

**Summary of findings:**
1. ✅ `_save_image()` uses wrong variable (`prefix` vs `filename`)
2. ✅ Missing trailing underscore breaks counter detection
3. ✅ Same bugs exist in `_save_video()` and `_save_text()`
4. ⚠️ Windows OSError may be related or environmental

**Confidence:** HIGH for the code bugs, MEDIUM for the Windows error root cause.

**Question for user:** Does this analysis look correct? Should I proceed with implementing the fixes?
