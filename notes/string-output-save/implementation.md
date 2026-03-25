# Implementation: String Output Save to File

**Date**: 2026-03-24  
**Status**: COMPLETE

---

## Changes Made

### File: `schema_nodes.py`

#### 1. Added `_save_text()` helper function (lines 134-147)

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

#### 2. Modified `SchemaStringParameter.execute()` (lines 265-269)

Added output mode handling at the end of the method:

```python
        if io_kind == "output":
            # Save text to file when in output mode, using name as filename
            file_info = _save_text(str(value), name)
            field["output_files"] = file_info

        return (value, field)
```

---

## Behavior

- **Input mode** (`io_kind = "input"`): No change - returns value and field as before
- **Output mode** (`io_kind = "output"`): 
  - Saves string to `.txt` file in ComfyUI output folder
  - Filename uses the `name` field (e.g., `my_prompt_00001.txt`)
  - Adds `output_files` metadata to field schema
  - Still returns value and field for downstream use

---

## Testing Checklist

- [ ] Create SchemaStringParameter node with `io_kind = "output"`
- [ ] Connect a string input to `value_in`
- [ ] Run workflow
- [ ] Verify `.txt` file created in output folder
- [ ] Verify filename matches the `name` field
- [ ] Verify file content matches the string value
