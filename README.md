# World Labs

Create with Atlas APIs and tools.

Agent skills for the World Labs API and Atlas for Blender, packaged as one plugin for Codex and Claude Code.

| Skill | What it does |
| --- | --- |
| `worldlabs` | Generate and edit images, estimate cameras and depth, and manage API tasks and assets. |
| `atlas-blender` | Import calibrated projects, pose images, inspect point clouds, generate views, and create native Gaussian splats in Blender. |

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

Atlas requires Blender 5.3+ and a separately installed Atlas extension. Blender MCP is strongly
recommended for agent access; Blender's Python Console, Text Editor, or background Python also work.
Gaussian splats require internal API access.

This skill targets the unreleased Blender Python API. Use an updated supplied extension build;
the currently published ZIP still uses the old CLI. See [setup](skills/atlas-blender/references/setup.md)
for installation and a read-only compatibility check.

## Try it

- “List the tasks available through the World Labs API.”
- “Find my open Atlas Blender session and inspect its frames without changing anything.”
- “Import this calibrated Atlas project and inspect its cameras and point clouds.”

## Development

Clone this repository and load it locally:

```sh
git clone https://github.com/worldlabsai/skills.git
cd skills
```

For Codex, register the checkout with `codex plugin marketplace add "$PWD"`, then install
`worldlabs@worldlabs`. After edits, remove and reinstall the plugin to refresh its cached copy.
For Claude Code, run `claude --plugin-dir "$PWD"` and restart the session after edits.

Validate the plugin metadata with `claude plugin validate --strict .`.

Use the [test scenarios](tests/scenarios.md) to check skill selection and tool behavior.
Both hosts share the same `skills/` content.

## License

Copyright 2026 World Labs Technologies, Inc.

The skills and helper code in this repository are licensed under [Apache-2.0](LICENSE).
World Labs names and logos remain trademarks of their respective owners. The World Labs API
and separately distributed Blender add-on are governed by their own terms and licenses.
