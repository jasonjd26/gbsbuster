# Jarvis

Jarvis is a **local** personal AI assistant that runs on your own machine,
powered by the [Claude API](https://www.anthropic.com/) (model
`claude-opus-4-8`, Anthropic's most capable model) via the official Anthropic
Python SDK. It has a **persistent long-term memory** stored in a local SQLite
database, so it can remember durable facts, preferences, and context about you
across sessions.

It is built to be private: **zero telemetry of any kind**. The only network
traffic Jarvis makes is to the Anthropic API to answer your messages.

## How it works

- Runs as an interactive command-line REPL.
- Sends your conversation to Claude using a manual tool-use loop.
- Claude can call built-in memory tools (`remember`, `recall`, `list_memories`,
  `forget`) plus `get_datetime`, so it proactively saves and looks up things
  worth remembering.
- All memories and message history live in a local SQLite file under
  `~/.jarvis`.

## Installation

### Option 1 — the bundled installer (recommended)

```sh
./install.sh
```

This creates an isolated virtualenv at `~/.jarvis/.venv`, installs Jarvis into
it, and symlinks the `jarvis` launcher into `~/.local/bin`. The installer
refuses to run as root and makes no remote calls beyond the `pip install` that
fetches the `anthropic` dependency.

Make sure `~/.local/bin` is on your `PATH`:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

### Option 2 — pip install (editable / development)

From the project root:

```sh
pip install -e .
```

This installs the `jarvis` console command into your current Python
environment.

## Setting your API key

Jarvis needs an Anthropic API key. Set it in your environment before chatting:

```sh
export ANTHROPIC_API_KEY="sk-ant-..."
```

Add that line to your shell profile (`~/.bashrc`, `~/.zshrc`, …) so it persists.

If the key is not set, Jarvis still starts and you can browse memories and use
`/help`, but chat turns are disabled until the key is present.

## Running

Once installed and your key is set:

```sh
jarvis
```

Or run it as a module without installing the launcher:

```sh
python -m jarvis
```

You will see a short banner, then a `you> ` prompt. Type a message and Jarvis
replies as `jarvis> `.

## Slash commands

| Command          | What it does                                  |
| ---------------- | --------------------------------------------- |
| `/help`          | List the available commands.                  |
| `/memories`      | Print the memories Jarvis has saved.          |
| `/forget <id>`   | Delete a saved memory by its numeric id.      |
| `/exit`, `/quit` | Leave Jarvis.                                 |

`Ctrl-D` (EOF) and `Ctrl-C` also exit gracefully.

## Where your data lives

Everything is stored locally under:

```
~/.jarvis/
├── .venv/        # virtualenv created by install.sh
└── jarvis.db     # SQLite database: your memories and message history
```

You can change the home directory with the `JARVIS_HOME` environment variable,
and the model with `JARVIS_MODEL` (defaults to `claude-opus-4-8`).

To wipe Jarvis's memory, simply delete `~/.jarvis/jarvis.db`.

## Privacy

Jarvis is designed to respect your privacy:

- **No telemetry, no analytics, no usage tracking, no beacons** — ever.
- The **only** network connection it makes is to the **Anthropic API** to
  generate responses, through the official `anthropic` Python SDK.
- All memory and conversation data stays on your machine in a local SQLite
  file. Nothing is uploaded anywhere except the message content you send to
  Claude when you ask it something.
