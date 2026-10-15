# World Labs

Create with Atlas APIs and tools.

Agent skills for the World Labs API and Atlas for Blender, packaged as one plugin for Codex and Claude Code.

| Skill | What it does |
| --- | --- |
| `worldlabs` | Generate and edit images, estimate cameras and depth, and manage API tasks and assets. |
| `atlas-blender` | Pose images, inspect RGBD, build grayboxes, arrange scenes, and generate views in Blender. |

## Install

### Codex

```sh
codex plugin marketplace add worldlabsai/skills
codex plugin add worldlabs@worldlabs
```

Start a new chat and invoke a skill, such as `$worldlabs:worldlabs` or `$worldlabs:atlas-blender`.

### Claude Code

```sh
claude plugin marketplace add worldlabsai/skills
claude plugin install worldlabs@worldlabs
```

Start a new session and invoke `/worldlabs:worldlabs` or `/worldlabs:atlas-blender`.

## Set up the tools

### World Labs API

Install the CLI with Node.js 24 or newer:

```sh
npm install -g @worldlabsai/cli@0.1.0
worldlabs auth login
worldlabs tasks list --json
```

Enter your API key in the CLI's private prompt. Make sure `worldlabs` is available in the agent's
shell. Task availability depends on your account's access.

### Atlas for Blender

The Blender skills require Blender 5.1 or newer, the Atlas Blender add-on, and Python 3.10 or newer.
The plugin includes the companion CLI. Download the [Atlas add-on ZIP](https://cdn.atlas-beta.worldlabs.ai/showcase/blender/worldlabs_atlas-0.1.0.zip)
and [SHA-256 checksum](https://cdn.atlas-beta.worldlabs.ai/showcase/blender/SHA256SUMS).
Install the ZIP through Blender's **Preferences > Get Extensions > Install from Disk** and enable Atlas.

Follow the [Blender setup guide](skills/atlas-blender/references/setup.md) to install the add-on
and verify the connection before editing a scene. Pose and generation also require a World Labs API key.

## Try it

- “List the tasks available through the World Labs API.”
- “Find my open Atlas Blender session and inspect its frames without changing anything.”
- “Build a medium-detail graybox from the Atlas frames in this scene.”

## Development

Clone this repository and load it locally:

```sh
git clone https://github.com/worldlabsai/skills.git
cd skills
```

For Codex, register the checkout with `codex plugin marketplace add "$PWD"`, then install
`worldlabs@worldlabs`. After edits, remove and reinstall the plugin to refresh its cached copy.
For Claude Code, run `claude --plugin-dir "$PWD"` and restart the session after edits.

Validate the plugin and run the Blender CLI tests:

```sh
claude plugin validate --strict .
PYTHONPATH=skills/atlas-blender/scripts python3 -m unittest discover -s tests -p 'test_*.py'
```

Use the [test scenarios](tests/scenarios.md) to check skill selection and tool behavior.
Both hosts share the same `skills/` content. Keep the bundled Blender CLI compatible with the
Atlas add-on release used for testing.

## License

Copyright 2026 World Labs Technologies, Inc.

The skills and helper code in this repository are licensed under [Apache-2.0](LICENSE).
World Labs names and logos remain trademarks of their respective owners. The World Labs API
and separately distributed Blender add-on are governed by their own terms and licenses.
