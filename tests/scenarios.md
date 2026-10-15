# Test scenarios

Run each prompt in a fresh Codex or Claude Code session with the plugin loaded. Record the host
version, selected skill, commands, and observed result. Keep API and Blender tests separate.

| Scenario | Prompt | Expected observation |
| --- | --- | --- |
| API discovery | Use the World Labs API skill to list the available tasks. Do not submit requests or upload files. | Runs CLI task discovery; reports actual task names. Missing executable or Node is reported with setup steps. |
| Authentication | Check whether the World Labs CLI is authenticated. Do not log in or change credentials. | Runs `auth status`; reports configured access or missing authentication without revealing a key. |
| Blender installation | Help me install Atlas in Blender. | Downloads the Atlas add-on ZIP from the setup guide, guides Install from Disk, then verifies the intended session. Does not install the CLI as an add-on. |
| Blender discovery | Use the Atlas Blender skill to list sessions. Do not change a scene or call the API. | Runs the bundled client; reports session PID and project or that no session exists. Never invents a connection. |
| Graybox workflow | Explain how you would build or refine a graybox from my Atlas frames. Do not execute anything. | Selects atlas-blender and loads references/image-to-graybox.md; inventories existing geometry and preserves editable sources. |

After the read-only checks pass, provide a specific image and output directory for one API task,
or identify a saved Blender project for a read-only `frames list` round trip. Generation tests
require account access and permission to use the selected input. Record returned operation IDs
and output paths. A wait timeout must resume the existing operation rather than submit again.
