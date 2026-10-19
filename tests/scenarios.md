# Test scenarios

Run each prompt in a fresh Codex or Claude Code session with the plugin loaded. Record the host
version, selected skill, and observed result. Keep API and Blender checks separate.

| Scenario | Prompt | Expected observation |
| --- | --- | --- |
| API discovery | Use the World Labs API skill to list the available tasks. Do not submit requests or upload files. | Runs CLI task discovery; reports actual task names. Missing executable or Node is reported with setup steps. |
| Authentication | Check whether the World Labs CLI is authenticated. Do not log in or change credentials. | Runs `auth status`; reports configured access or missing authentication without revealing a key. |
| Blender setup | Help me set up Atlas in Blender. | Requires Blender 5.3+, explains GUI installation and API settings, and that the currently published CDN ZIP lacks the new `bpy.ops.atlas.command` API. |
| Blender discovery | Use the Atlas Blender skill to inspect frames in my open scene without changing anything. | Checks for `bpy.ops.atlas.command`, calls `frames.list`, and reports returned frames or a clear error. It does not assume a connected session. |
| Import and pose | Import this camera/image/depth project into Blender and inspect the result. | Uses `project.import` for calibrated exports, preserving their poses; uses `pose` only for unposed images and reports job status without blocking Blender's event loop. |
| Scene placement | Arrange these independently posed images into a coherent scene. | Reads scene-placement concepts, chooses its own placement and inspection methods, and may toggle point clouds or inspect camera views. Does not require a numerical alignment procedure. |
| Atlas generation | Generate views from the visible Atlas cameras in this scene. | Calls normal generation Atlas and depth-conditioned generation Chisel; uses actual camera names and reports online access or API errors clearly. |
| Gaussian splat | Create a native Gaussian splat from my Atlas context images. | Checks Blender 5.3+ and internal API access. Usually gathers at least 8 context views for a compact scene and 16 or more for a larger scene, with usable depth and matching resolution; distinguishes this guidance from the endpoint's two-image lower limit. |
