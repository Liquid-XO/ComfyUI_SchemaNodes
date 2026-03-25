# ComfyUI SchemaNodes

A node pack that lets you define typed input/output parameters directly in your ComfyUI workflow — so agents can run it like an API.

## The Problem

ComfyUI workflows are visual and flexible, but that makes them hard for agents to work with. There's no clean way to say "here are my inputs, here are my outputs" in a machine-readable format. An agent looking at a workflow JSON just sees a sea of nodes with no clear entry or exit points.

## The Solution

SchemaNodes gives you parameter nodes that act as typed field declarations:

- **Input parameters** (`io_kind=input`) — the values an agent needs to provide before running the workflow
- **Output parameters** (`io_kind=output`) — the values the agent gets back after execution

Drop these nodes into your workflow, wire them up, and you've defined a clean request/response contract.

## Designed for Tooling

SchemaNodes doesn't include agent tooling — it's the foundation you build on. The idea is:

1. Your tool parses a workflow JSON and extracts all SchemaNodes
2. It builds a typed schema (inputs the agent must provide, outputs it will receive)
3. The agent fills in input values, your tool injects them into the workflow
4. Send to ComfyUI API, collect outputs

Each parameter node emits a `SCHEMA_FIELD` object with field metadata — name, description, type, constraints, defaults. Everything a schema parser needs to build a clean interface.

## Included Nodes

| Node | Type | Use Case |
|------|------|----------|
| `Schema String Parameter` | string | Prompts, text inputs/outputs |
| `Schema Integer Parameter` | int | Dimensions, counts, seeds |
| `Schema Float Parameter` | float | Strengths, scales, weights |
| `Schema Boolean Parameter` | bool | Toggles, flags |
| `Schema Enum Parameter` | enum | Fixed choices (samplers, models) |
| `Schema Image Parameter` | image | Input images, output renders |
| `Schema Video Parameter` | video | Input clips, output animations |
| `Schema Audio Parameter` | audio | Input audio, output sound |

## Visual Distinction

The frontend extension color-codes nodes by `io_kind` so inputs and outputs are visually distinct in the graph. You'll know at a glance which nodes define your workflow's interface.
