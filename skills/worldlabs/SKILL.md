---
name: worldlabs
description: Generate and edit scene images, estimate cameras and depth, or extract meshes with the World Labs CLI.
license: Apache-2.0
---

# World Labs

Use `worldlabs` for the Developer API. The examples use a POSIX shell. Requires Node 24+ and `@worldlabsai/cli`. If `worldlabs` is missing, locate the user-provided CLI executable or install `@worldlabsai/cli@0.1.0` with npm. Use the resolved executable consistently; do not assume plugin installation installs the CLI. Run `worldlabs --help` for command syntax.

## Choose a task

| Task | Purpose |
| --- | --- |
| `atlasTextToImage` | Generate starting images from a description of an environment. |
| `images2PosedRGBD` | Estimate cameras and depth from images of a scene. |
| `atlasGenerate` | Generate new viewpoints using posed RGBD context. |
| `atlasChisel` | Generate posed images from a prompt and optional depth layouts. |
| `atlasMasked` | Fill masked regions across posed images. |
| `splats2Mesh` | Extract a mesh from a Gaussian splat scene. |

Read [How To Use Atlas](https://marble5.worldlabs.ai/docs/how-to-use-atlas) before choosing model inputs, calculating cameras, or chaining tasks. It explains scene data, model behavior, and the requirements that affect results. Follow its task or camera links when you need exact fields or geometry calculations. `worldlabs tasks list` reports SDK task names; account access can differ.

## Submit and inspect

Upload a local image:

```sh
worldlabs assets upload photo.jpg --json > asset.json
```

Write `request.json` as `{"frames":[{"imageAsset":{"assetId":"<id>"}}]}`, replacing `<id>` with the uploaded asset's `id` from `asset.json`.

```sh
worldlabs tasks run images2PosedRGBD --request request.json --wait --json > result.json
```

Use `--request -` to read JSON from stdin. Results go to stdout; diagnostics and the submission's idempotency key go to stderr. Preserve the key and reuse it with `--idempotency-key <key>` and the same request if submission is interrupted.

A timeout stops local waiting, not server work. Resume with `worldlabs operations wait <operation-id> --json`. Check a completed operation's `error` before reading `response`. Download returned assets with `worldlabs assets download <asset-id> --out result.png`. Inspect the outputs before using them in another task; keep each image, camera, depth, and confidence together.

## Authentication

Check `worldlabs auth status`. If login is needed, have the user run `worldlabs auth login` in their own terminal and enter the key privately. Never request keys in chat or put them in command arguments. Automation can supply `WLT_API_KEY`. The key selects the API project and billing; a successful status check verifies asset access, not every task permission.
