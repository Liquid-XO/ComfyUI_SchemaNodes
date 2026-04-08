# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed

- **SCHEMA_FIELD output removed from all parameter nodes**: Nodes now return only the typed value, not the field metadata tuple
  - `RETURN_TYPES` changed from `("TYPE", "SCHEMA_FIELD")` to `("TYPE",)` for all 8 parameter node classes
  - `RETURN_NAMES` changed from `("value", "field")` to `("value",)`
  - Internal `_field_schema()` method retained for potential future use (Phase 2 cleanup pending)
  - Simplifies node connections — downstream nodes receive values directly

### Added

- **Configurable image save format**: `SchemaImageParameter` now supports `save_format` and `quality` options for output mode
  - `save_format`: Choose between "webp" (default), "png", or "jpg"
  - `quality`: 1-100 (default 90) — applies to WebP and JPEG, ignored for PNG
  - JPEG automatically converts RGBA → RGB (no alpha support)
  - WebP default provides better compression than previous PNG-only behavior

### Fixed

- **ComfyCloud image/video parameter support**: `SchemaImageParameter` and `SchemaVideoParameter` now accept both string filenames (local ComfyUI) and dict format `{filename, subfolder, type}` (ComfyCloud storage)
  - Updated `_load_image()` and `_load_video()` to handle dict input via `folder_paths.get_directory_by_type()`
  - Backward compatible — existing string filename workflows unaffected

## [0.3.0] - 2026-03-25

### Fixed

- **Save functions pattern mismatch**: Corrected `_save_image()`, `_save_video()`, and `_save_text()` to match ComfyUI's native `SaveImage` pattern
  - Use `filename` instead of `prefix` from `get_save_image_path()` return value
  - Add trailing underscore to filename pattern for proper counter detection
  - Pass image/video dimensions to `get_save_image_path()` for template variable support (`%width%`, `%height%`)
  - Fixes Windows OSError when saving images with SchemaImageParameter

### Added

- **String output save to file**: `SchemaStringParameter` now saves text to `.txt` file when `io_kind="output"`
  - Uses the `name` field as filename prefix
  - Saves to ComfyUI output folder with auto-incrementing counter
  - Adds `output_files` metadata to field schema

## [0.2.0] - 2026-03-13

### Added

- **io_kind-aware media handling** for `SchemaImageParameter` and `SchemaVideoParameter`
  - Input mode: Load filename from input folder → convert to `[B, H, W, C]` tensor
  - Output mode: Take tensor → save to output folder → return file metadata
- Helper functions: `_load_image()`, `_save_image()`, `_load_video()`, `_save_video()`
- `filename_prefix` input for output mode on media parameter nodes
- `frame_rate` input for `SchemaVideoParameter`

### Changed

- `BaseSchemaMediaParameter` now accepts `value_in` of any type (`"*"`) for flexibility
- `SchemaVideoParameter` returns `IMAGE` type (batched frames, VHS-style)

## [0.1.0] - 2026-03-11

### Added

- Initial release of ComfyUI_INOUT (SchemaNodes)
- Schema parameter nodes for typed workflow field declarations:
  - `Schema String Parameter`
  - `Schema Integer Parameter`
  - `Schema Float Parameter`
  - `Schema Boolean Parameter`
  - `Schema Enum Parameter`
  - `Schema Image Parameter`
  - `Schema Video Parameter`
  - `Schema Audio Parameter`
- Each node outputs:
  - Real typed workflow value for graph wiring
  - `SCHEMA_FIELD` object with field metadata for tooling
- `io_kind` field to mark parameters as `input` or `output`
- Frontend extension for color-coding input/output nodes
- Field metadata support: `name`, `description`, `default`, type-specific constraints

[Unreleased]: https://github.com/Liquid-XO/ComfyUI_SchemaNodes/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Liquid-XO/ComfyUI_SchemaNodes/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Liquid-XO/ComfyUI_SchemaNodes/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Liquid-XO/ComfyUI_SchemaNodes/releases/tag/v0.1.0
