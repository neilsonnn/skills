# Image to graybox

The default detail level is **medium**. Keep all levels aligned to the same RGBD evidence:

- **Low:** broad room boundaries and large objects.
- **Medium:** the default; add meaningful parts such as a table top and legs or a cup body and
  handle, plus a few semantic primitives where the views support them.
- **High:** finer supported parts and silhouette breaks, while remaining a coarse editable graybox.

Detail controls modeling granularity, not placement accuracy. Check alignment at every level.
Finish each semantic asset as one mesh object: join a cup's body and handle, or a pot's body, rim,
and foot with Blender's native Join. Clicking any part in Object Mode must move the whole asset.
The pieces remain editable as disconnected mesh islands in Edit Mode; named vertex groups can
identify them. Parenting separate meshes alone does not meet this interaction requirement.
Keep independent assets, rugs, and room surfaces separately selectable. Register the finished
asset meshes as grayboxes and refine their pieces in Edit Mode on later passes.

Follow [Atlas connection instructions](../SKILL.md#connect-before-editing) first.
Use computer use to inspect every visible, depth-ready RGB view and its native Atlas point cloud in
Blender. Use simple mesh primitives to communicate occupied space, boundaries, and major openings;
do not model surface detail. Read
[scene-placement.md](scene-placement.md) before placing independent
estimates.

Preserve the user's scene. For a new graybox task, work in a separate saved Blender project. Do
not delete or replace existing scene content unless the user explicitly requests it.

## Inspect and plan

1. Select the intended Atlas session and inventory all visible, depth-ready frames, their RGB views,
   native point clouds, poses, filters, and existing graybox objects.
2. Inspect each source camera view, then orbit through floor-level, overhead, and side views. Note
   floors, walls, openings, large objects, uncertain boundaries, and scene regions already modeled.
3. Use confidence filtering when confidence varies and is useful. If confidence is constant or
   uninformative, isolate geometry with depth bounds and display crops. Crops do not remove pixels
   from API context.
4. Map independent estimates to distinct observed regions. Their camera frusta may intersect, but
   their grayboxed surfaces must not conflict or duplicate one another. Joint reconstructions and
   pose-conditioned generated views may overlap; inspect their consistency.

## Build iteratively

1. Before each pass, inventory prior primitives by the source region and structure they represent.
2. Update existing primitives affected by new evidence, then add primitives only for missing
   observed regions.
   Do not create duplicate floors, walls, or objects, and do not destructively replace the graybox.
3. Choose simple cubes, cylinders, spheres, cones, planes, or other mesh primitives with Blender's
   native tools or trusted, visible Blender Python entered through the console. Use the Atlas CLI
   for buffer, pose, filter, context, and graybox commands.
4. Match the main silhouette: boxes for walls and cabinets, cylinders for columns or pots,
   and scaled spheres for rounded objects. Keep primitives coarse and editable. Use a small number
   of objects with clear names and ordinary transforms; represent uncertainty with conservative
   extents rather than invented detail. Join each asset's parts before registering or baking it.
   Preserve world-space placement, materials, UVs, and the evaluated result of part-specific
   modifiers when joining existing parts. Put the origin at a useful asset center or base.
5. Recheck every source camera plus floor-level and overhead or side views. Correct penetrations,
   floating primitives, missing walkable space, mismatched scale, and duplicated regions.
   Test moving a finished asset by selecting its body and then another visible part; both must
   select the same object. Restore its transform after testing.

## Inspect the projection

1. Select the primitives and choose **Use Selected as Grayboxes** in the Atlas panel. The CLI
   equivalent is `graybox.assign` with `objectNames`. Any mesh primitive can be registered;
   the command preserves its geometry.
2. Turn **Project Context on Grayboxes** on in Material Preview or Rendered mode.
   Use **Projection strength** to blend from lit gray (0) to the full texture (1), without making
   geometry transparent. The material responds to lights; use a studio light that reveals shape.
   `graybox.projection` takes `enabled`, optional `strength` (0-1), and `depthTolerance` in scene units.
   `graybox.list` reports registered primitives, context IDs, and projection errors.
3. Inspect the surfaces from multiple angles. Every visible, depth-ready camera contributes where it sees the surface and its depth agrees within
   the tolerance. Hidden cameras, including those hidden through a collection or view layer, are
   excluded. Point display filters do not change the projected images.
4. Turn the toggle off to judge the plain geometry. If projection is missing, check context, paths,
   face orientation, and primitive alignment before increasing depth tolerance. Large tolerances can
   paint through surfaces. Overlapping views blend and can ghost if they disagree.

## Compare alignment

Use the alignment comparison after a placement pass to identify object-specific depth adjustments.
Prefer RGB views when choosing semantic shapes and boundaries, then use depth residuals to adjust the
corresponding primitive. Inspect multiple views and solid geometry before changing a shared surface.

`graybox.compare` accepts optional `frameIds`, `tolerance`, and `stride`. It defaults to the active
frame, the scene tolerance (0.25 scene units), and stride 4; stride must be a positive integer from 1
through 64. It evaluates visible registered mesh first-hit depths through calibrated source cameras and
honors source depth, confidence, and normalized XY filters. Display `preview_stride` and `point_size`
are ignored. Metrics include per-object sample count, median signed and absolute error, p90 absolute
error, fraction within tolerance, plus separate coverage and missing-hit counts.

Use **Compare Active Depth** or **Compare Context Depth** in the UI to compute snapshots on demand. Retrieve the
latest in-memory result with `graybox.comparison`; it is empty after a new load or before comparison,
and includes a stale flag. `graybox.show_comparison` opens `overlay`, `residual`, or `rgb` for an
optional frame (active by default). Recompute after geometry, camera, or filter edits. The comparison
does not fit geometry or treat source depth as ground truth.

Read aggregate metrics with care: a large wall can hide poor alignment on a small object, and contour
error can arise from object size or silhouette rather than pure translation. Compare conflicting
generated and source depth before minimizing one against the other.

Save the project separately and report which frames informed each region, what existing primitives
were updated, what was added, and where the graybox remains uncertain. Include depth measurements
and disagreements across views; passing extension tests does not establish modeling accuracy.
