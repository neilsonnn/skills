---
name: atlas-blender
description: Use Atlas in Blender to import camera/image/depth projects, pose images into point clouds, generate views with Atlas or Chisel, and create native Gaussian splats.
license: Apache-2.0
---

# Atlas for Blender

Enable Atlas in Blender 5.3+; see [setup](references/setup.md) for installation and read-only verification. [Blender MCP](https://www.blender.org/lab/mcp-server/) is strongly recommended for agent access, but optional; agents can also run Python through Blender’s Python Console, Text Editor, or command line.

Run Atlas's operators inside Blender's Python environment. Read [commands](references/commands.md) when you need call syntax, import formats, or job handling.

Import exports containing camera JSON, images, depth, and confidence directly; they already have poses. Inspect unfamiliar layouts rather than assuming an exact folder structure or re-posing calibrated images.

When assembling posed images into a shared scene, read [scene placement](references/scene-placement.md) for the concepts. Choose your own placement and inspection methods.

Camera visibility controls Atlas context. **Points** toggles point clouds independently. Use ordinary Blender tools and scene state for everything else.

For Atlas concepts, see the [Atlas documentation](https://atlas-beta.worldlabs.ai/docs/how-to-use-atlas).
