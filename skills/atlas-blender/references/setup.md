# Set up Atlas for Blender

Requires Blender 5.3 or newer. Gaussian splats require internal API access.
The Atlas extension is installed separately from this agent plugin. This skill requires an updated
supplied build with `bpy.ops.atlas.command`. The published
[ZIP](https://cdn.atlas-beta.worldlabs.ai/showcase/blender/worldlabs_atlas-0.1.0.zip) and
[checksum](https://cdn.atlas-beta.worldlabs.ai/showcase/blender/SHA256SUMS) still point to the older
CLI build; use the supplied preview until that download is updated.

## Install and configure

1. In the intended Blender installation, open **Preferences > Get Extensions > Install from Disk**;
   select the supplied extension ZIP and enable Atlas.
2. For online posing and generation, enable **Allow Online Access** in Blender Preferences and
   enter the World Labs API key in the Atlas sidebar under **Settings > Connection**. Local imports
   work offline. Keep keys out of chat.
3. Keep the Blender project open. Blender MCP is recommended for agent access; Python Console,
   Text Editor, or background Python also work.

## Verify the add-on

Run this from Blender's Python environment. It lists Atlas frames without editing scene objects or
making an online request:

```python
import bpy
import json

if bpy.app.version < (5, 3, 0):
    raise RuntimeError("Atlas requires Blender 5.3 or newer")

try:
    bpy.ops.atlas.command.get_rna_type()
except KeyError as exc:
    raise RuntimeError("Enable an Atlas build with bpy.ops.atlas.command support") from exc

bpy.ops.atlas.command(request_json=json.dumps({"command": "frames.list", "args": {}}))
response = json.loads(bpy.context.window_manager.atlas_result)
if not response.get("ok"):
    raise RuntimeError(response.get("error", {}).get("message", "Atlas request failed"))
print(response["result"])
```

An empty frame list is valid. For operator syntax and import, posing, generation, and job commands,
see [commands](commands.md).
