# OpenClaw Tele CLI Channel Plugin

Channel plugin for OpenClaw that connects Telegram through local `tele-cli` sessions and daemon RPC.

## Features

- Inbound Telegram messages via `tele daemon start --rpc-stdio`
- Outbound replies through daemon RPC (with CLI fallback)
- Account/session split:
  - `daemonSession` for inbound monitor
  - `sendSession` for outbound sends
- DM policy controls (`open`, `pairing`, `disabled`)
- Allowlists for DM and groups
- Optional direct-message session isolation (`sessionIsolate`)
- Ignore specific user peers (`ignorePeerIds`)
- Ignore all inbound while daemon account is online (`self_online` from `tele-cli`)

## Install

Install from local path:

```bash
openclaw plugins install .../tele-cli/openclaw-telecli-plugin
```

Or if repo root manifest is present:

```bash
openclaw plugins install .../tele-cli
```

Then restart gateway:

```bash
openclaw gateway restart
```

## Prerequisites

- `tele-cli` installed and authenticated sessions available
- OpenClaw gateway configured and running

Useful checks:

```bash
tele auth list
openclaw channels status --json
```

## Configuration

Configure in `~/.openclaw/openclaw.json` under `channels.telecli`.

Example:

```json
{
  "channels": {
    "telecli": {
      "enabled": true,
      "telePath": "/Users/huanan/Developer/tele-cli/.venv/bin/tele",
      "daemonSession": "CurrentDaemon",
      "sendSession": "Inston",
      "dmPolicy": "allowlist",
      "allowFrom": ["*"],
      "groupPolicy": "allowlist",
      "groupAllowFrom": ["*"],
      "sessionIsolate": true,
      "ignorePeerIds": ["xxxxx"]
    }
  }
}
```

Apply changes:

```bash
openclaw gateway restart
```

## Config Options

- `telePath`:
  Path to `tele` executable.
- `session`:
  Default session if split sessions are not specified.
- `daemonSession`:
  Session used by daemon monitor (inbound).
- `sendSession`:
  Session used for outbound replies.
- `configFile`:
  Optional `tele-cli` config path.
- `dmPolicy`:
  `open` | `pairing` | `disabled`.
- `allowFrom`:
  Allowed direct users (supports `*`).
- `groupPolicy`:
  `open` | `allowlist` | `disabled`.
- `groupAllowFrom`:
  Allowed group senders.
- `sessionIsolate`:
  If true, each direct sender gets isolated OpenClaw session key.
- `ignorePeerIds`:
  List of user peer IDs to ignore for direct/user dialogs.
- `textChunkLimit`, `chunkMode`, `blockStreaming`, `responsePrefix`:
  Outbound formatting/chunking behavior.

## `ignorePeerIds` Behavior

When inbound dialog type is user/direct, plugin checks peer/sender ID against `ignorePeerIds`.
If matched, message is dropped before routing and no reply is generated.

Example update:

```bash
openclaw config set channels.telecli.ignorePeerIds '["8486211156"]' --json
openclaw gateway restart
```

## Online Ignore Behavior

`tele-cli` daemon emits `self_online` state in inbound events.
If `self_online` is `true`, plugin ignores all inbound messages.

Purpose: avoid bot auto-replies while your Telegram account is actively online.

## Troubleshooting

- No inbound:
  - Check daemon session is valid: `tele --session <name> me`
  - Check channel status: `openclaw channels status --json`
- No outbound:
  - Prefer separate `sendSession`
  - Validate target entity exists in send session dialogs
- Session lock / sqlite lock:
  - Avoid sharing the same session concurrently across multiple writers
- Plugin load conflicts:
  - If duplicate plugin warnings appear, keep only one active plugin path

## Dev Notes

- Source folder: `openclaw-telecli-plugin`
- Channel id: `telecli`
- Plugin id: `tele-cli`
