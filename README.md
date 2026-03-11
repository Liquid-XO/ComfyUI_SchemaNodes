# ComfyUI INOUT

`ComfyUI_INOUT` is a schema-first node pack for defining workflow parameters directly inside a ComfyUI graph.

Each parameter node behaves like a typed field declaration on a Pydantic model:

- it exposes a real workflow value you can wire into the graph
- it emits a machine-readable schema field object for tooling and agents
- it lets you mark the field as `input` or `output`
- it surfaces field metadata such as `name`, `description`, `default`, and type-specific constraints

## Included nodes

- `Schema String Parameter`
- `Schema Integer Parameter`
- `Schema Float Parameter`
- `Schema Boolean Parameter`
- `Schema Enum Parameter`
- `Schema Image Parameter`
- `Schema Video Parameter`
- `Schema Audio Parameter`

Each parameter node outputs:

- a real typed workflow value you can wire into the graph
- a `SCHEMA_FIELD` object carrying field metadata for tooling

The frontend extension color-codes parameter nodes so `input` and `output` fields are visually distinct in the graph.
