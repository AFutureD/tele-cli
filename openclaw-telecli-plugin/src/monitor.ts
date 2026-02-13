import { spawn } from "node:child_process";
import readline from "node:readline";
import {
  createReplyPrefixOptions,
  logInboundDrop,
  resolveControlCommandGate,
  type OpenClawConfig,
  type RuntimeEnv,
} from "openclaw/plugin-sdk";
import { resolveTeleCliAccount, type ResolvedTeleCliAccount } from "./accounts.js";
import {
  registerTeleDaemonRpcClient,
  unregisterTeleDaemonRpcClient,
  type TeleDaemonRpcClient,
} from "./rpc.js";
import { getTeleCliRuntime } from "./runtime.js";
import { sendMessageTeleCli } from "./send.js";

const CHANNEL_ID = "telecli" as const;

type PeerLike = {
  user_id?: number;
  chat_id?: number;
  channel_id?: number;
};

type NormalizedPeer = {
  id: string;
  type: "user" | "chat" | "channel" | "unknown";
  userId?: string;
  chatId?: string;
  channelId?: string;
};

type TeleDaemonMessage = {
  id?: string | number;
  out?: boolean;
  post?: boolean;
  message?: string;
  date?: unknown;
  peer_id?: unknown;
  from_id?: unknown;
  sender_id?: unknown;
  sender_name?: unknown;
  sender_username?: unknown;
  chat_title?: unknown;
  chat_username?: unknown;
  self_online?: boolean;
};

type TeleDaemonPacket =
  | {
      type: "ready";
      mode?: string;
    }
  | {
      type: "event";
      event: string;
      payload?: unknown;
    }
  | {
      type: "response";
      id: string;
      ok: boolean;
      result?: unknown;
      error?: string;
    };

export type TeleDaemonMonitorOptions = {
  accountId?: string;
  config?: OpenClawConfig;
  runtime?: RuntimeEnv;
  abortSignal?: AbortSignal;
  statusSink?: (patch: { connected?: boolean; lastInboundAt?: number; lastOutboundAt?: number }) => void;
};

function buildGlobalArgs(params: { session?: string; configFile?: string }): string[] {
  const args: string[] = [];
  if (params.session?.trim()) {
    args.push("--session", params.session.trim());
  }
  if (params.configFile?.trim()) {
    args.push("--config", params.configFile.trim());
  }
  return args;
}

function asPeerLike(value: unknown): PeerLike | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const candidate = value as Record<string, unknown>;
  const out: PeerLike = {};
  if (typeof candidate.user_id === "number") {
    out.user_id = candidate.user_id;
  }
  if (typeof candidate.chat_id === "number") {
    out.chat_id = candidate.chat_id;
  }
  if (typeof candidate.channel_id === "number") {
    out.channel_id = candidate.channel_id;
  }
  return out.user_id || out.chat_id || out.channel_id ? out : null;
}

function toPeerIdString(peer: unknown): string | null {
  if (typeof peer === "number" || typeof peer === "string") {
    const raw = String(peer).trim();
    return raw || null;
  }
  const p = asPeerLike(peer);
  if (!p) {
    return null;
  }
  if (typeof p.user_id === "number") {
    return String(p.user_id);
  }
  if (typeof p.chat_id === "number") {
    return String(-p.chat_id);
  }
  if (typeof p.channel_id === "number") {
    return String(-(1_000_000_000_000 + p.channel_id));
  }
  return null;
}

function isDirectPeer(peer: unknown): boolean {
  const p = asPeerLike(peer);
  return Boolean(p?.user_id);
}

function normalizePeer(peer: unknown): NormalizedPeer | null {
  const id = toPeerIdString(peer);
  if (!id) {
    return null;
  }
  const p = asPeerLike(peer);
  if (!p) {
    return { id, type: "unknown" };
  }
  if (typeof p.user_id === "number") {
    return { id, type: "user", userId: String(p.user_id) };
  }
  if (typeof p.chat_id === "number") {
    return { id, type: "chat", chatId: String(p.chat_id) };
  }
  if (typeof p.channel_id === "number") {
    return { id, type: "channel", channelId: String(p.channel_id) };
  }
  return { id, type: "unknown" };
}

function buildPeerContext(params: {
  peer: unknown;
  from: unknown;
  sender: unknown;
  direct: boolean;
  senderName?: unknown;
  senderUsername?: unknown;
  chatTitle?: unknown;
  chatUsername?: unknown;
}) {
  const peer = normalizePeer(params.peer);
  const from = normalizePeer(params.from);
  const rawSender = normalizePeer(params.sender);
  const sender =
    (!rawSender || rawSender.type === "unknown" ? from : rawSender) ??
    (params.direct
      ? {
          id: peer?.id ?? "unknown",
          type: "user" as const,
          userId: peer?.id,
        }
      : null);

  const senderUsername =
    typeof params.senderUsername === "string"
      ? params.senderUsername.replace(/^@/, "").trim() || undefined
      : undefined;
  const senderName =
    typeof params.senderName === "string" ? params.senderName.trim() || undefined : undefined;
  const chatTitle = typeof params.chatTitle === "string" ? params.chatTitle.trim() || undefined : undefined;
  const chatUsername =
    typeof params.chatUsername === "string"
      ? params.chatUsername.replace(/^@/, "").trim() || undefined
      : undefined;

  const senderType = sender?.type ?? "unknown";
  const fallbackSenderLabel =
    senderType === "user"
      ? `Telegram user ${sender?.id ?? "unknown"}`
      : senderType === "channel"
        ? `Telegram channel ${sender?.id ?? "unknown"}`
        : `Telegram peer ${sender?.id ?? "unknown"}`;
  const senderLabel = senderName ?? fallbackSenderLabel;
  const conversationLabel = params.direct
    ? senderLabel
    : chatTitle
      ? `${chatTitle} id:${peer?.id ?? "unknown"}`
      : chatUsername
        ? `@${chatUsername} id:${peer?.id ?? "unknown"}`
    : peer?.type === "channel"
      ? `Telegram channel ${peer.id}`
      : `Telegram chat ${peer?.id ?? "unknown"}`;

  const context: Record<string, string | undefined> = {
    PeerId: peer?.id,
    PeerType: peer?.type,
    PeerUserId: peer?.userId,
    PeerChatId: peer?.chatId,
    PeerChannelId: peer?.channelId,
    FromPeerId: from?.id,
    FromPeerType: from?.type,
    FromPeerUserId: from?.userId,
    FromPeerChatId: from?.chatId,
    FromPeerChannelId: from?.channelId,
    SenderPeerId: sender?.id,
    SenderPeerType: sender?.type,
    SenderPeerUserId: sender?.userId,
    SenderPeerChatId: sender?.chatId,
    SenderPeerChannelId: sender?.channelId,
    SenderName: senderLabel,
    SenderUsername: senderUsername,
    GroupSubject: params.direct ? undefined : chatTitle,
    ConversationLabel: conversationLabel,
  };

  return {
    context,
    senderLabel,
    senderUsername,
    groupSubject: params.direct ? undefined : chatTitle,
    conversationLabel,
  };
}

function parseTimestamp(value: unknown): number | undefined {
  if (typeof value === "number") {
    return value > 1_000_000_000_000 ? value : value * 1000;
  }
  if (typeof value === "string") {
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }
  return undefined;
}

function buildIsolatedDirectSessionKey(params: {
  agentId: string;
  channelId: string;
  accountId: string;
  senderId: string;
}): string {
  const sender = params.senderId.trim().toLowerCase();
  if (!sender) {
    return `agent:${params.agentId}:main`;
  }
  return `agent:${params.agentId}:${params.channelId}:${params.accountId}:direct:${sender}`;
}

function normalizeAllowEntry(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    return "";
  }
  if (trimmed === "*") {
    return "*";
  }
  return trimmed
    .replace(/^(telecli|tele|tg):/i, "")
    .replace(/^user:/i, "")
    .toLowerCase();
}

function normalizeAllowList(values: Array<string | number> | undefined): string[] {
  return Array.from(
    new Set(
      (values ?? [])
        .map((entry) => normalizeAllowEntry(String(entry)))
        .filter(Boolean),
    ),
  );
}

function isSenderAllowed(senderId: string, allowFrom: string[]): boolean {
  if (allowFrom.length === 0) {
    return false;
  }
  if (allowFrom.includes("*")) {
    return true;
  }
  return allowFrom.includes(normalizeAllowEntry(senderId));
}

async function deliverTeleCliReply(params: {
  payload: { text?: string; mediaUrls?: string[]; mediaUrl?: string };
  target: string;
  account: ResolvedTeleCliAccount;
  replyTo?: number;
  statusSink?: TeleDaemonMonitorOptions["statusSink"];
}): Promise<void> {
  const text = params.payload.text?.trim() ?? "";
  const mediaList = params.payload.mediaUrls?.length
    ? params.payload.mediaUrls
    : params.payload.mediaUrl
      ? [params.payload.mediaUrl]
      : [];
  const fileList: string[] = [];
  const linkList: string[] = [];
  for (const media of mediaList) {
    const item = String(media).trim();
    if (!item) {
      continue;
    }
    if (
      item.startsWith("/") ||
      item.startsWith("./") ||
      item.startsWith("../") ||
      item.startsWith("file://")
    ) {
      fileList.push(item.startsWith("file://") ? item.slice("file://".length) : item);
      continue;
    }
    linkList.push(item);
  }
  const mediaBlock = linkList.length ? linkList.map((url) => `Attachment: ${url}`).join("\n") : "";
  const combined = text && mediaBlock ? `${text}\n\n${mediaBlock}` : text || mediaBlock;
  if (!combined.trim()) {
    return;
  }
  await sendMessageTeleCli(params.target, combined, {
    accountId: params.account.accountId,
    telePath: params.account.telePath,
    session: params.account.sendSession ?? params.account.session,
    configFile: params.account.configFile,
    replyTo: params.replyTo,
    file: fileList.length ? fileList : undefined,
  });
  params.statusSink?.({ lastOutboundAt: Date.now() });
}

export async function monitorTeleDaemon(opts: TeleDaemonMonitorOptions): Promise<void> {
  const core = getTeleCliRuntime();
  const cfg = opts.config ?? core.config.loadConfig();
  const account = resolveTeleCliAccount({
    cfg,
    accountId: opts.accountId,
  });
  if (!account.configured) {
    throw new Error(`telecli account ${account.accountId} is not configured`);
  }

  const logger = core.logging.getChildLogger({
    channel: CHANNEL_ID,
    accountId: account.accountId,
  });

  const handleInbound = async (msg: TeleDaemonMessage) => {
    if (!msg || msg.out) {
      return;
    }
    if (account.config.dropWhenSelfOnline !== false && msg.self_online === true) {
      return;
    }
    const rawBody = (msg.message ?? "").trim();
    if (!rawBody) {
      return;
    }

    const peerId = toPeerIdString(msg.peer_id);
    if (!peerId) {
      return;
    }
    const direct = isDirectPeer(msg.peer_id);
    const senderId =
      toPeerIdString(msg.from_id) ??
      toPeerIdString(msg.sender_id) ??
      (direct ? peerId : "unknown");
    const ignorePeerIds = normalizeAllowList(account.config.ignorePeerIds);
    const isUserDialog =
      direct ||
      Boolean(asPeerLike(msg.from_id)?.user_id) ||
      Boolean(asPeerLike(msg.sender_id)?.user_id);
    const ignoredPeer = ignorePeerIds.includes(normalizeAllowEntry(peerId));
    const ignoredSender = ignorePeerIds.includes(normalizeAllowEntry(senderId));

    if (isUserDialog && (ignoredPeer || ignoredSender)) {
      return;
    }

    const dmPolicy = account.config.dmPolicy ?? "pairing";
    const groupPolicy = account.config.groupPolicy ?? cfg.channels?.defaults?.groupPolicy ?? "allowlist";

    const configAllowFrom = normalizeAllowList(account.config.allowFrom);
    const configGroupAllowFrom = normalizeAllowList(account.config.groupAllowFrom);
    const storeAllowFrom = normalizeAllowList(
      await core.channel.pairing.readAllowFromStore(CHANNEL_ID).catch(() => []),
    );
    const effectiveAllowFrom = Array.from(new Set([...configAllowFrom, ...storeAllowFrom]));
    const effectiveGroupAllowFrom = Array.from(
      new Set([
        ...(configGroupAllowFrom.length > 0 ? configGroupAllowFrom : configAllowFrom),
        ...storeAllowFrom,
      ]),
    );

    const allowTextCommands = core.channel.commands.shouldHandleTextCommands({
      cfg,
      surface: CHANNEL_ID,
    });
    const hasControlCommand = core.channel.text.hasControlCommand(rawBody, cfg);
    const useAccessGroups = cfg.commands?.useAccessGroups !== false;
    const senderAllowedForCommands = isSenderAllowed(
      senderId,
      direct ? effectiveAllowFrom : effectiveGroupAllowFrom,
    );
    const commandGate = resolveControlCommandGate({
      useAccessGroups,
      authorizers: [
        {
          configured: (direct ? effectiveAllowFrom : effectiveGroupAllowFrom).length > 0,
          allowed: senderAllowedForCommands,
        },
      ],
      allowTextCommands,
      hasControlCommand,
    });
    const commandAuthorized = direct
      ? dmPolicy === "open" || senderAllowedForCommands
      : commandGate.commandAuthorized;

    if (direct) {
      if (dmPolicy === "disabled") {
        return;
      }
      if (dmPolicy !== "open" && !senderAllowedForCommands) {
        if (dmPolicy === "pairing") {
          const { code, created } = await core.channel.pairing.upsertPairingRequest({
            channel: CHANNEL_ID,
            id: senderId,
            meta: { name: senderId },
          });
          if (created) {
            const pairingReply = core.channel.pairing.buildPairingReply({
              channel: CHANNEL_ID,
              idLine: `Your Telegram user id: ${senderId}`,
              code,
            });
            await sendMessageTeleCli(peerId, pairingReply, {
              accountId: account.accountId,
              telePath: account.telePath,
              session: account.sendSession ?? account.session,
              configFile: account.configFile,
            }).catch((err) => {
              logger.debug?.(`pairing reply failed: ${String(err)}`);
            });
            opts.statusSink?.({ lastOutboundAt: Date.now() });
          }
        }
        return;
      }
    } else {
      if (groupPolicy === "disabled") {
        return;
      }
      if (groupPolicy === "allowlist") {
        if (effectiveGroupAllowFrom.length === 0 || !senderAllowedForCommands) {
          return;
        }
      }
    }

    if (!direct && commandGate.shouldBlock) {
      logInboundDrop({
        log: (line) => logger.debug?.(line),
        channel: CHANNEL_ID,
        reason: "control command (unauthorized)",
        target: senderId,
      });
      return;
    }

    const route = core.channel.routing.resolveAgentRoute({
      cfg,
      channel: CHANNEL_ID,
      accountId: account.accountId,
      peer: {
        kind: direct ? "direct" : "group",
        id: direct ? senderId : peerId,
      },
    });
    const sessionKey =
      direct && account.config.sessionIsolate === true
        ? buildIsolatedDirectSessionKey({
            agentId: route.agentId,
            channelId: CHANNEL_ID,
            accountId: route.accountId,
            senderId,
          })
        : route.sessionKey;

    const mentionRegexes = core.channel.mentions.buildMentionRegexes(cfg, route.agentId);
    const wasMentioned = core.channel.mentions.matchesMentionPatterns(rawBody, mentionRegexes);
    if (!direct) {
      const requireMention = core.channel.groups.resolveRequireMention({
        cfg,
        channel: CHANNEL_ID,
        accountId: account.accountId,
        groupId: peerId,
      });
      const shouldBypassMention = hasControlCommand && commandAuthorized;
      if (requireMention && !wasMentioned && !shouldBypassMention) {
        return;
      }
    }

    const peerMeta = buildPeerContext({
      peer: msg.peer_id,
      from: msg.from_id,
      sender: msg.sender_id,
      direct,
      senderName: msg.sender_name,
      senderUsername: msg.sender_username,
      chatTitle: msg.chat_title,
      chatUsername: msg.chat_username,
    });
    const timestamp = parseTimestamp(msg.date) ?? Date.now();
    const chatType = direct ? "direct" : "group";
    const body = core.channel.reply.formatInboundEnvelope({
      channel: "Telegram",
      from: peerMeta.conversationLabel,
      timestamp,
      body: rawBody,
      chatType,
      sender: {
        id: senderId,
        name: peerMeta.senderLabel,
        username: peerMeta.senderUsername,
      },
    });

    const messageSid = msg.id != null ? String(msg.id) : `${Date.now()}`;
    const to = `telecli:${peerId}`;
    const ctxPayload = core.channel.reply.finalizeInboundContext({
      Body: body,
      BodyForAgent: rawBody,
      RawBody: rawBody,
      CommandBody: rawBody,
      From: direct ? `telecli:${senderId}` : `telecli:group:${peerId}`,
      To: to,
      SessionKey: sessionKey,
      AccountId: route.accountId,
      ChatType: chatType,
      ConversationLabel: peerMeta.conversationLabel,
      GroupSubject: peerMeta.groupSubject,
      SenderId: senderId,
      SenderName: peerMeta.senderLabel,
      SenderUsername: peerMeta.senderUsername,
      Provider: CHANNEL_ID,
      Surface: CHANNEL_ID,
      MessageSid: messageSid,
      Timestamp: timestamp,
      WasMentioned: direct ? undefined : wasMentioned,
      CommandAuthorized: commandAuthorized,
      OriginatingChannel: CHANNEL_ID,
      OriginatingTo: to,
      ...peerMeta.context,
    });

    const storePath = core.channel.session.resolveStorePath(cfg.session?.store, {
      agentId: route.agentId,
    });
    await core.channel.session.recordInboundSession({
      storePath,
      sessionKey: ctxPayload.SessionKey ?? sessionKey,
      ctx: ctxPayload,
      updateLastRoute: direct
        ? {
            sessionKey: route.mainSessionKey,
            channel: CHANNEL_ID,
            to: senderId,
            accountId: route.accountId,
          }
        : undefined,
      onRecordError: (err) => {
        logger.error(`failed updating session meta: ${String(err)}`);
      },
    });

    core.channel.activity.record({
      channel: CHANNEL_ID,
      accountId: account.accountId,
      direction: "inbound",
      at: timestamp,
    });

    const { onModelSelected, ...prefixOptions } = createReplyPrefixOptions({
      cfg,
      agentId: route.agentId,
      channel: CHANNEL_ID,
      accountId: account.accountId,
    });

    await core.channel.reply.dispatchReplyWithBufferedBlockDispatcher({
      ctx: ctxPayload,
      cfg,
      dispatcherOptions: {
        ...prefixOptions,
        deliver: async (payload) => {
          const replyTo =
            msg.id != null && Number.isFinite(Number(msg.id)) ? Number(msg.id) : undefined;
          await deliverTeleCliReply({
            payload: payload as { text?: string; mediaUrls?: string[]; mediaUrl?: string },
            target: peerId,
            account,
            replyTo,
            statusSink: opts.statusSink,
          });
        },
        onError: (err, info) => {
          logger.error(`telecli ${info.kind} reply failed: ${String(err)}`);
        },
      },
      replyOptions: {
        onModelSelected,
        disableBlockStreaming:
          typeof account.config.blockStreaming === "boolean"
            ? !account.config.blockStreaming
            : undefined,
      },
    });

    opts.statusSink?.({ lastInboundAt: Date.now() });
  };

  const argv = [
    account.telePath,
    ...buildGlobalArgs({
      session: account.daemonSession ?? account.session,
      configFile: account.configFile,
    }),
    "--format",
    "json",
    "daemon",
    "start",
    "--rpc-stdio",
  ];

  logger.info(`starting tele-cli daemon: ${argv.join(" ")}`);

  const child = spawn(argv[0], argv.slice(1), {
    stdio: ["pipe", "pipe", "pipe"],
  });
  if (!child.stdin || !child.stdout || !child.stderr) {
    throw new Error("tele-cli daemon process does not expose stdio pipes");
  }

  const onAbort = () => {
    child.kill("SIGTERM");
  };
  opts.abortSignal?.addEventListener("abort", onAbort, { once: true });

  const rlOut = readline.createInterface({ input: child.stdout });
  const rlErr = readline.createInterface({ input: child.stderr });

  let chain = Promise.resolve();
  let reqSeq = 0;
  const pending = new Map<
    string,
    {
      resolve: (value: unknown) => void;
      reject: (reason?: unknown) => void;
      timer: ReturnType<typeof setTimeout>;
    }
  >();

  const sendRpc = (method: string, params: Record<string, unknown>): Promise<unknown> =>
    new Promise((resolve, reject) => {
      const reqId = `${Date.now()}-${++reqSeq}`;
      const timer = setTimeout(() => {
        pending.delete(reqId);
        reject(new Error(`tele daemon rpc timeout: ${method}`));
      }, 30_000);
      pending.set(reqId, { resolve, reject, timer });

      const line = `${JSON.stringify({ id: reqId, method, params })}\n`;
      child.stdin?.write(line, (err) => {
        if (!err) {
          return;
        }
        const item = pending.get(reqId);
        if (!item) {
          return;
        }
        clearTimeout(item.timer);
        pending.delete(reqId);
        reject(err);
      });
    });

  const rpcClient: TeleDaemonRpcClient = {
    sendMessage: async ({ receiver, message, entityType, replyTo, file }) => {
      const result = await sendRpc("send_message", {
        receiver,
        message,
        ...(entityType ? { entity_type: entityType } : {}),
        ...(typeof replyTo === "number" ? { reply_to: replyTo } : {}),
        ...(file?.length ? { file } : {}),
      });
      const parsed = (result ?? {}) as { sent?: boolean; receiver?: string };
      return {
        sent: parsed.sent === true,
        receiver: parsed.receiver ?? receiver,
      };
    },
    close: () => {
      try {
        child.stdin?.write(`${JSON.stringify({ id: "shutdown", method: "stop", params: {} })}\n`);
      } catch {
        // ignore cleanup failures
      }
    },
  };
  registerTeleDaemonRpcClient(account.accountId, rpcClient);

  rlErr.on("line", (line) => {
    if (core.logging.shouldLogVerbose()) {
      logger.debug?.(`tele-cli stderr: ${line}`);
    }
  });

  const enqueueInbound = (work: () => Promise<void>): void => {
    chain = chain.then(work).catch((err) => {
      logger.error(`tele-cli inbound handler error: ${String(err)}`);
    });
  };

  rlOut.on("line", (line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return;
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(trimmed);
    } catch {
      if (core.logging.shouldLogVerbose()) {
        logger.debug?.(`tele-cli non-json line: ${trimmed}`);
      }
      return;
    }

    if (parsed && typeof parsed === "object" && "type" in parsed) {
      const packet = parsed as TeleDaemonPacket;
      if (packet.type === "ready") {
        opts.statusSink?.({ connected: true });
        return;
      }
      // Responses must be handled immediately; do not queue behind inbound work.
      if (packet.type === "response") {
        const item = pending.get(packet.id);
        if (!item) {
          return;
        }
        clearTimeout(item.timer);
        pending.delete(packet.id);
        if (packet.ok) {
          item.resolve(packet.result ?? {});
          return;
        }
        item.reject(new Error(packet.error ?? "unknown rpc error"));
        return;
      }
      if (packet.type === "event" && packet.event === "new_message") {
        if (packet.payload && typeof packet.payload === "object") {
          enqueueInbound(() => handleInbound(packet.payload as TeleDaemonMessage));
        }
        return;
      }
    }

    enqueueInbound(async () => {
      // Backward compatibility with pre-RPC daemon payloads.
      if (Array.isArray(parsed)) {
        for (const entry of parsed) {
          if (entry && typeof entry === "object") {
            await handleInbound(entry as TeleDaemonMessage);
          }
        }
        return;
      }
      if (parsed && typeof parsed === "object") {
        await handleInbound(parsed as TeleDaemonMessage);
      }
    });
  });

  await new Promise<void>((resolve, reject) => {
    child.once("error", (err) => {
      unregisterTeleDaemonRpcClient(account.accountId);
      for (const item of pending.values()) {
        clearTimeout(item.timer);
        item.reject(err);
      }
      pending.clear();
      opts.abortSignal?.removeEventListener("abort", onAbort);
      rlOut.close();
      rlErr.close();
      reject(err);
    });
    child.once("close", (code, signal) => {
      unregisterTeleDaemonRpcClient(account.accountId);
      const closeErr = new Error(
        `tele-cli daemon exited (code=${code ?? "null"}, signal=${signal ?? "none"})`,
      );
      for (const item of pending.values()) {
        clearTimeout(item.timer);
        item.reject(closeErr);
      }
      pending.clear();
      opts.abortSignal?.removeEventListener("abort", onAbort);
      rlOut.close();
      rlErr.close();
      opts.statusSink?.({ connected: false });
      chain.finally(() => {
        if (opts.abortSignal?.aborted || signal === "SIGTERM") {
          resolve();
          return;
        }
        if (code === 0) {
          resolve();
          return;
        }
        reject(closeErr);
      });
    });
  });
}
