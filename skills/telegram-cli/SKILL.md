---
name: Telegram CLI Usage Guide
description: Use `tele` to authenticate, list dialogs, and fetch messages from Telegram.
---

# Telegram CLI Usage Guide

## Overview

Use `tele` to authenticate, list dialogs, and fetch messages from Telegram directly from the terminal.


## Setup

- Check if `tele` is already installed: `which tele`
- Install with `uv` (recommended): `uv tool install git+https://github.com/AFutureD/tele-cli`
- Verify install: `tele -V`
- Config file: `tele` reads `~/.config/tele/config.toml` by default and will create it on first run;

## Notice

- Call `tele -h` once before running any command for the first time in the session.
- Always use JSON output: always pass `-f json` to `tele` (example: `tele -f json me`).
- In each session, confirm authentication before running non-auth commands: run `tele -f json me`.
- Commands under `tele auth ...` do not require an existing authenticated session.

## Quick Start

1. Read help once: `tele -h`
2. Log in (interactive prompts): `tele auth login`
3. Confirm who you are: `tele -f json me`
4. List dialogs and find a `dialog_id`: `tele -f json dialog list`
5. Fetch recent messages from a dialog:
   - `tele -f json message list <dialog_id> -n 20`

## Session Management

Global options:

- `--config <path>`: alternate config file (default: `~/.config/tele/config.toml`)
- `--session <name>`: use a specific session file by name (listed by `tele auth list`)

Login / logout:

- `tele auth login` (creates a local session; prompts for phone, code, and optional 2FA password)
- `tele auth login --switch` (log in and make the new session active)
- `tele auth logout` (logs out of the selected session)

List and switch sessions:

- `tele auth list`
- `tele auth switch --uid <user_id>`
- `tele auth switch --username <username>` (accepts `@alice` or `alice`)
- `tele auth switch --session <session_name>`

Where sessions live on disk (macOS/Linux default):

- Sessions folder: `~/.config/tele/sessions/`
- Current activated session symlink: `~/.config/tele/sessions/Current.session`

## Dialog List

List all dialogs (users, groups, channels):

- `tele -f json dialog list`

Notes:

- For `-f text`, the output follows the template:
  - `[TYPE.UI.STATE] [UNREAD COUNT] [DIALOG_ID] NAME`
  - `TYPE`: `U` user, `G` group, `C` channel
  - `UI`: `P` pinned, `A` archived, `-` normal
  - `STATE`: `M` muted, `-` not muted
- For `-f json`, each dialog includes keys like `name`, `entity` (with `id`), `unread_count`, and the latest `message`.

## Message List

Fetch messages from a dialog:

- `tele -f json message list <dialog_id>`

Common options:

- Limit count: `-n <num>` (example: `tele -f json message list <dialog_id> -n 20`)
- Pagination: `--offset_id <message_id>` (fetch around/older than a known message id; `offset_id` is excluded)
- Output order: `--order asc|desc`
- Time filters:
  - `--from "<natural language or date>"`
  - `--to "<natural language or date>"`
  - `--range "<natural language range>"` (overrides `--from/--to`, special: `"this week"`)

Examples:

- `tele -f json message list 1375282077 -n 10`
- `tele -f json message list 1375282077 --range "last week"`
- `tele -f json message list 1375282077 --from "2025-02-05" --to "yesterday"`

## Send Message

// TODO:
