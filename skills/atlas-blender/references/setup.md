# Set up Atlas for Blender

Requires Blender 5.1 or newer and Python 3.10 or newer. The Atlas add-on is distributed
separately from this plugin. Download [worldlabs_atlas-0.1.0.zip](https://cdn.atlas-beta.worldlabs.ai/showcase/blender/worldlabs_atlas-0.1.0.zip)
and use its local path for installation. A [SHA-256 checksum](https://cdn.atlas-beta.worldlabs.ai/showcase/blender/SHA256SUMS)
is also available.
Do not substitute the Blender MCP add-on or install `atlas_cli.py` as an add-on.

## Install the add-on

1. Open the Blender installation the user intends to use.
2. In **Preferences > Get Extensions**, open the menu and choose **Install from Disk**.
   Select the separately downloaded `worldlabs_atlas-0.1.0.zip` and enable Atlas.
3. In a 3D View, open the sidebar with **N** and find the **Atlas** tab. Keep Blender open.

## Verify the connection

Resolve `ATLAS_CLI` to `../scripts/atlas_cli.py` relative to this reference file, or use the
user's configured path. Set `ATLAS_PYTHON` to a Python 3.10+ executable, such as `python3`.

```sh
"$ATLAS_PYTHON" "$ATLAS_CLI" sessions list
```

Choose a session with `live: true` and match its PID and `blendFile` to the intended project, then set `ATLAS_SESSION` to
its `sessionId` and run:

```sh
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" frames list
```

Require `ok: true`. An empty frame list is valid. These checks do not upload images or require an API key.

| Problem | Check |
| --- | --- |
| No Atlas tab | Confirm the extension installed successfully and is enabled in this Blender version. |
| No sessions | Keep Blender open and responsive. Confirm Atlas is enabled. |
| Several sessions | Match the project and PID; do not silently choose a different scene. |
| Session shown in Blender but absent from the CLI | If `ATLAS_SESSION_ROOT` is set, use the same directory in Blender and the agent's shell. |
| Command timeout | Close blocking Blender dialogs and inspect the scene or jobs before retrying. |

## Enable API operations

Pose and generation require **Allow Online Access** in Blender Preferences and a World Labs API
key with the relevant task access. Enter the key in Atlas settings; it is saved in Blender-wide
preferences. Alternatively, set `WLT_API_KEY` in Blender's environment. Never ask users to paste
a key into chat.
