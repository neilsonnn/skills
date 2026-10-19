# Scene placement

A posed image is a calibrated camera observing part of a scene. Its point cloud estimates the
surfaces visible in that image; it is not a complete object or room. Missing backsides, occlusions,
and uncertain depth are normal.

Independently posed images can have different origins, orientations, and scales. Think of them as
observations of regions you want to place in one coherent scene. Overlapping observations can be
useful when they describe the same surfaces; conflicting floors, walls, or objects indicate that
the estimates or their placement disagree. Unrelated concept images do not establish a measured
reconstruction of one physical place.

Jointly reconstructed images already share a coordinate system. Preserve their relationships when
placing the group. Atlas-generated images are conditioned on their context and target cameras, but
that does not guarantee that every generated surface agrees with the existing scene.

Use your judgment and ordinary Blender tools to place and inspect images. Looking through source
cameras or exploring other viewpoints can help. Toggle **Points** on or off whenever useful;
measurements and numerical alignment are optional, not a required procedure. Move a frame's camera
to move its child cloud with it. If adjusting scale, Atlas supports positive uniform camera scale.

Camera visibility determines generation context. Hiding only a point cloud does not remove its
image from context. Point display filters and crops affect the preview; Atlas receives the full
RGBD images from eligible visible cameras. Choose context that represents the scene you intend to
generate, using visual inspection or other methods you find useful.
