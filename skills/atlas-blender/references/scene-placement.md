# Place images in a shared room

Atlas frames are calibrated cameras with child point clouds. Their surfaces have geometry only
where the source image saw something; back faces and disoccluded areas may be empty.

Treat independently posed frames like photographs taken while walking through a house. Each
estimate contributes a distinct observed region to the assembled scene. Camera frusta may cross,
but visible floor, wall, and object patches from independent estimates must not occupy conflicting
or overlapping space. Overlap is appropriate only when the images were jointly reconstructed as
overlapping views, or when a generated view was pose-conditioned on existing context. Generated
consistency is intended rather than guaranteed, so inspect it before integration.

## Measure in the right coordinates

| Quantity | Convention |
|---|---|
| Blender world | Z up; camera looks down local -Z, local +Y up |
| API world | Y up; RUB camera-to-world pose |
| API to Blender world | `(x, y, z)` becomes `(x, -z, y)` |
| Raw image coordinates | Top-down rows; pixel centers `(x + 0.5, y + 0.5)` |
| Depth | Positive optical-axis depth, not Euclidean distance from camera |
| Source scale | Unknown metric accuracy for independent estimates |
| Display crop | Normalized X/Y; Y increases downward |

`frames.inspect` supplies current evaluated `matrixWorld`, API pose, and calibration. Use this
matrix after parent or constraint edits. With focal lengths `fx, fy`, principal point `cx, cy`,
and depth `d`, a pixel center has camera position:

```text
((x + 0.5 - cx) * d / fx, -(y + 0.5 - cy) * d / fy, -d)
```

Transform the homogeneous position by the Blender camera's evaluated matrix. A uniform camera
scale scales these depths. `buffers.sample` already returns the corresponding world point.
Inspect actual exported metadata for array shapes and filenames; do not infer channel meaning
from an image's display colors. Preview images normalize depth for viewing; use raw float arrays
for measurements.

## Assemble a room

1. Choose one image as the room anchor. Select multiple high-confidence floor pixels away from
   objects and boundaries. Fit a plane; rotate its upward normal onto world +Z and translate it
   to Z=0. Reject outliers and verify residuals on held-out floor samples. If confidence is noisy,
   filter by confidence first. If confidence is constant, use depth bounds and display crops.
2. Choose a recognizable length, such as a doorway height, and state its assumed size. Apply
   one positive uniform scale to the whole frame. Rotate around Z to align its dominant wall
   with the room axes. Do not use nonuniform scale or edit calibrated source camera lenses.
3. For each additional independent image, isolate its useful observed region with display crops
   and depth bounds. Align its floor/contact samples to Z=0 and match its estimated scale to the
   anchor. Place that region beside existing observations without stacking duplicate floors,
   walls, or objects. The camera may sit inside another frame's frustum.
4. Re-sample world positions, measure floor residuals and wall positions, and inspect from source
   cameras, a floor-level view, and overhead or side views. Move or filter conflicting patches;
   do not preserve duplicate room shells merely because each source-camera view looks plausible.
5. Save the transforms, source frame IDs, crop values, assumed dimensions, and measured residuals.
   Reopen the saved project and recheck them. Describe the result as an assembled RGBD scene;
   unrelated concept images do not establish a measured reconstruction of one physical room.

For a target camera, let `forward = normalize(look_at - location)`,
`right = normalize(cross(forward, world_up))`, and `up = cross(right, forward)`.
The rotation columns are `(right, up, -forward)` and the last column is the location.
Choose a nonparallel up vector if looking directly along world Z.

`point_size` multiplies the depth-calibrated pixel radius; start near 1.0, not a radius in metres.
At oblique viewpoints, gaps and stretched depth boundaries may remain even with larger points.

Display crops do not crop generation context. Generation receives complete RGBD bundles from
visible, depth-ready cameras. Blender camera visibility controls context for generation, projection,
Compare Context, and baking. Hidden cameras are excluded even when named by context ID or hidden
through a collection or view layer. Hiding only a cloud
changes display. Start generated viewpoints near one coherent anchor frame, inspect
the result, and expand context only when the returned surfaces agree.
