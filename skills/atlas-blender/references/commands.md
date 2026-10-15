# Atlas command recipes

Set `ATLAS_CLI` to the absolute client path and `ATLAS_SESSION` to a discovered session ID.
Set `ATLAS_PYTHON` to a Python 3.10+ interpreter (for example, `python3`). Replace frame IDs and file paths with
values from the session. Run `--help` on a subcommand for its current options.

```sh
"$ATLAS_PYTHON" "$ATLAS_CLI" sessions list
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" frames list
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" frames inspect "$FRAME_ID"
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" buffers sample "$FRAME_ID" --pixel 640 600
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" buffers export "$FRAME_ID" --output /tmp/atlas-frame
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" pose --files /absolute/room.jpg --mode separate --wait
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" filters set "$FRAME_ID" z_min=0.2 z_max=12 x_min=0.1 x_max=0.9
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" frames hide "$FRAME_ID"
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" jobs status
```

`generate` accepts only depth-ready frames whose cameras are visible. Blender camera visibility is the context switch across generation, projection, Compare Context, and baking, including visibility inherited from collections and view layers. Hiding only a cloud changes display. Use `frames hide FRAME_ID` and `frames hide FRAME_ID --show` to control camera visibility.

Omitted generation prompt, enhancement, and depth options inherit the scene's saved Generate
settings; omitted `--context-ids` uses all visible, depth-ready frames. Explicit `--prompt`,
`--enhance-prompt` / `--no-enhance-prompt`, and `--return-depth` / `--no-return-depth` override them.
After importing an enhanced result, Atlas saves `promptUsed`, reuses it as Prompt, and turns
enhancement off unless the user edited those settings during the request. Do not re-enhance the
saved text on every call. `jobs status` includes `promptUsed` when returned.

**Generate from View** submits from the current viewport or viewed camera. Its adjacent camera
toggle enters or leaves preview. **Import and Pose Images** has its own row, followed by
collapsed **Generate settings** and **Show Atlas Context**. Selecting a camera shows **View**,
**Delete**, **Duplicate**, and **Hide**, plus **Show Image**, **Image Opacity**, **RGB**, **Depth**,
and **Confidence**. Point filters are inside collapsed **Image settings**. The strip and native
camera selection drive the same selected-camera controls. **CLI Actions** contains comparison
and maintenance operations. The import file picker contains estimate/reconstruct and
preserve-framing options.
Use raw `frames.duplicate` with `frameId` to copy a frame camera and its cloud independently.

Set a row-major camera-to-world matrix. This example preserves the Blender camera's identity
orientation and places it at `(0, -4, 1.6)`; it looks down world -Z. For a room view, calculate
the rotation as described in the placement reference instead of copying this orientation.

```sh
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" camera set "$FRAME_ID" \
  --matrix-world '[[1,0,0,0],[0,1,0,-4],[0,0,1,1.6],[0,0,0,1]]'
```

For UI generation, inspect the target camera in camera view with Passepartout enabled before
submitting. Adjust its pose and lens against that preview, then use **Generate from View**; the
request records the exact evaluated pose and lens shown in the preview. The CLI path below remains
available when an explicit target camera is required.

`raw` accepts a JSON file or JSON text. The CLI supplies schema version, UUID, and deadline.
A saved file is preferable for matrices and multiline prompts.

```json
{"command":"camera.create","args":{"name":"Room target","matrixWorld":[[1,0,0,0],[0,0,-1,-4],[0,1,0,1.6],[0,0,0,1]]}}
```

```sh
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" raw target.json
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" generate --target-names 'Room target' \
  --context-ids "$FRAME_ID" --return-depth --prompt 'A coherent concrete room' --wait
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" raw '{"command":"cache.pack","args":{}}'
```

Raw commands also include `frames.select`, `frames.view`, `frames.reset_calibration`,
`buffers.open`, `jobs.resume`, `jobs.import`, and `cache.relink`. Use the recipes below for supported arguments; do not guess undocumented command fields. Inside Blender, the namespace-independent
entry point is `bpy.ops.atlas.command(request_json=json.dumps(request))`; read the JSON reply
from `bpy.context.window_manager.atlas_result`.

Inspect `ok`, `error`, and `revision` in each response. Use `--expected-revision` where supported
when a human may be editing concurrently. Keep a request ID when retrying an uncertain operation.

## Generate from scene geometry

Use `chisel` when the user wants geometry-conditioned images. It renders visible
scene surfaces as depth-only context and does not send the existing images or mesh
files. This is separate from `generate`, which continues to use visible RGBD frames.
Your API account must have access to `atlasChisel`. Use `chisel --help` for sampling
options. In Blender, enable **Generate from graybox depth (Chisel)** in **Generate settings**.
Use selected perspective cameras for multiple views.

```sh
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" --timeout 300 chisel \
  --target-names 'Room camera A' 'Room camera B' \
  --prompt 'A warm plaster room' --return-depth --wait --timeout-secs 1800
```

Preview target cameras before submitting. Single-view results are RGB only; use
at least two translated cameras and `--return-depth` when subsequent RGBD
projection, generation, or baking needs the outputs. Chisel returns reconstructed
depth, not the original rendered depth. It does not modify the source graybox.

## Graybox projection

Create and position simple mesh primitives (cubes, cylinders, spheres, and others) with Blender tools, then register their exact object names:

```sh
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" raw '{"command":"graybox.assign","args":{"objectNames":["Graybox floor","Graybox wall"]}}'
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" raw '{"command":"graybox.projection","args":{"enabled":true,"strength":0.5,"depthTolerance":0.5}}'
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" raw '{"command":"graybox.list"}'
```

Use `enabled:false` to restore the primitives' normal materials. Assignment is repeatable; it does not
create geometry or replace material slots. `strength` blends lit gray (0) with the
projected color (1); the surface stays opaque. The depth tolerance uses Blender scene units.

## Graybox alignment comparison

Compare registered mesh first-hit depths with source depth through calibrated source cameras:

```sh
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" raw '{"command":"graybox.compare","args":{"frameIds":["FRAME_ID"],"tolerance":0.25,"stride":4}}'
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" raw '{"command":"graybox.comparison","args":{}}'
"$ATLAS_PYTHON" "$ATLAS_CLI" --session "$ATLAS_SESSION" raw '{"command":"graybox.show_comparison","args":{"frameId":"FRAME_ID","channel":"overlay"}}'
```

`frameIds` defaults to the active frame. `tolerance` is positive scene units and defaults to the
scene setting (0.25); `stride` is a positive integer from 1 through 64 and defaults to 4. Results
use positive optical-axis depth and do not assume scene units are meters. Source depth, confidence,
and normalized XY filters apply. Display `preview_stride` and `point_size` are ignored. Each view
reports per-object sample count, median signed and absolute depth error, p90 absolute error, fraction
within tolerance, and separate coverage and missing-hit counts.

The UI actions **Compare Active Depth** and **Compare Context Depth** compute snapshots on demand. **Compare
Context Depth** uses all visible, depth-ready frames, matching generation context. Outputs are
stored below the companion `alignment/<runid>` directory: `report.json`, per-view `arrays.npz` with
`rgb`, `estimatedDepth`, `grayboxDepth`, `residual`, `validMask`, `sourceMask`, and `objectIndex`,
and `overlay.png`, `residual.png`, and `rgb.png`. Overlay colors are blue for too close, red for too
far, and magenta for valid source depth without a graybox hit; excluded pixels retain RGB. Heatmaps
use white for zero error and saturate at +/-2*tolerance.

`graybox.comparison` returns the latest in-memory report and a stale flag, or an empty result before
comparison and after a new load. `graybox.show_comparison` defaults to the active frame and the
`overlay` channel; `residual` and `rgb` are also supported. It opens an existing non-Atlas Image
Editor or splits a view, and returns the path in headless mode. Recompute after geometry, camera, or
filter edits. The command does not fit geometry or treat source depth as ground truth.

Global metrics can hide poor alignment on small objects behind a large wall area. Contour error can
reflect object size or silhouette rather than pure translation; compare conflicting generated and
source depth before minimizing either one blindly.
