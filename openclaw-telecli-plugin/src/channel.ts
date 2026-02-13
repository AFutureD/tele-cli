import {
  applyAccountNameToChannelSection,
  DEFAULT_ACCOUNT_ID,
  deleteAccountFromConfigSection,
  formatPairingApproveHint,
  migrateBaseNameToDefaultAccount,
  normalizeAccountId,
  setAccountEnabledInConfigSection,
  type ChannelPlugin,
} from "openclaw/plugin-sdk";
import { type ResolvedTeleCliAccount, listTeleCliAccountIds, resolveDefaultTeleCliAccountId, resolveTeleCliAccount } from "./accounts.js";
import { teleCliChannelConfigSchema } from "./config-schema.js";
import { monitorTeleDaemon } from "./monitor.js";
import { getTeleCliRuntime } from "./runtime.js";
import { sendMessageTeleCli } from "./send.js";

const meta = {
  id: "telecli",
  label: "Tele CLI",
  selectionLabel: "Tele CLI (daemon)",
  detailLabel: "Tele CLI",
  docsPath: "/channels/telegram",
  docsLabel: "telegram",
  blurb: "Use local tele-cli daemon events for Telegram messaging.",
  systemImage: "paperplane",
  order: 78,
  quickstartAllowFrom: true,
} as const;

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

export const teleCliPlugin: ChannelPlugin<ResolvedTeleCliAccount> = {
  id: "telecli",
  meta,
  pairing: {
    idLabel: "telegramUserId",
    normalizeAllowEntry,
    notifyApproval: async ({ cfg, id }) => {
      const account = resolveTeleCliAccount({ cfg });
      await sendMessageTeleCli(id, "OpenClaw: your access has been approved.", {
        accountId: account.accountId,
        telePath: account.telePath,
        session: account.session,
        configFile: account.configFile,
      });
    },
  },
  capabilities: {
    chatTypes: ["direct", "group"],
    media: true,
    reactions: false,
    threads: false,
    blockStreaming: true,
  },
  reload: {
    configPrefixes: ["channels.telecli"],
  },
  configSchema: teleCliChannelConfigSchema,
  config: {
    listAccountIds: (cfg) => listTeleCliAccountIds(cfg),
    resolveAccount: (cfg, accountId) => resolveTeleCliAccount({ cfg, accountId }),
    defaultAccountId: (cfg) => resolveDefaultTeleCliAccountId(cfg),
    setAccountEnabled: ({ cfg, accountId, enabled }) =>
      setAccountEnabledInConfigSection({
        cfg,
        sectionKey: "telecli",
        accountId,
        enabled,
        allowTopLevel: true,
      }),
    deleteAccount: ({ cfg, accountId }) =>
      deleteAccountFromConfigSection({
        cfg,
        sectionKey: "telecli",
        accountId,
        clearBaseFields: ["telePath", "session", "configFile", "name"],
      }),
    isConfigured: (account) => account.configured,
    describeAccount: (account) => ({
      accountId: account.accountId,
      name: account.name,
      enabled: account.enabled,
      configured: account.configured,
      telePath: account.telePath,
      session: account.session,
      daemonSession: account.daemonSession,
      sendSession: account.sendSession,
      configFile: account.configFile,
      sessionIsolate: account.config.sessionIsolate,
      ignorePeerIds: account.config.ignorePeerIds,
      dropWhenSelfOnline: account.config.dropWhenSelfOnline,
    }),
    resolveAllowFrom: ({ cfg, accountId }) =>
      (resolveTeleCliAccount({ cfg, accountId }).config.allowFrom ?? []).map((entry) =>
        String(entry),
      ),
    formatAllowFrom: ({ allowFrom }) =>
      allowFrom.map((entry) => normalizeAllowEntry(String(entry))).filter(Boolean),
  },
  security: {
    resolveDmPolicy: ({ cfg, accountId, account }) => {
      const resolvedAccountId = accountId ?? account.accountId ?? DEFAULT_ACCOUNT_ID;
      const useAccountPath = Boolean(cfg.channels?.telecli?.accounts?.[resolvedAccountId]);
      const basePath = useAccountPath
        ? `channels.telecli.accounts.${resolvedAccountId}.`
        : "channels.telecli.";
      return {
        policy: account.config.dmPolicy ?? "pairing",
        allowFrom: account.config.allowFrom ?? [],
        policyPath: `${basePath}dmPolicy`,
        allowFromPath: basePath,
        approveHint: formatPairingApproveHint("telecli"),
        normalizeEntry: normalizeAllowEntry,
      };
    },
    collectWarnings: ({ account, cfg }) => {
      const defaultGroupPolicy = cfg.channels?.defaults?.groupPolicy;
      const groupPolicy = account.config.groupPolicy ?? defaultGroupPolicy ?? "allowlist";
      if (groupPolicy !== "open") {
        return [];
      }
      return [
        '- Tele CLI groups: groupPolicy="open" allows any member to trigger the bot. Set channels.telecli.groupPolicy="allowlist" + channels.telecli.groupAllowFrom to restrict senders.',
      ];
    },
  },
  messaging: {
    normalizeTarget: (raw) => {
      const trimmed = raw.trim();
      if (!trimmed) {
        return undefined;
      }
      return trimmed.replace(/^(telecli|tele|tg):/i, "");
    },
    targetResolver: {
      looksLikeId: (raw) => /^-?\d+$/.test(raw.trim()) || /^(telecli|tele|tg):/i.test(raw.trim()),
      hint: "<peer_id>",
    },
  },
  setup: {
    resolveAccountId: ({ accountId }) => normalizeAccountId(accountId),
    applyAccountName: ({ cfg, accountId, name }) =>
      applyAccountNameToChannelSection({
        cfg,
        channelKey: "telecli",
        accountId,
        name,
      }),
    validateInput: () => null,
    applyAccountConfig: ({ cfg, accountId, input }) => {
      const namedConfig = applyAccountNameToChannelSection({
        cfg,
        channelKey: "telecli",
        accountId,
        name: input.name,
      });
      const next =
        accountId !== DEFAULT_ACCOUNT_ID
          ? migrateBaseNameToDefaultAccount({
              cfg: namedConfig,
              channelKey: "telecli",
            })
          : namedConfig;
      if (accountId === DEFAULT_ACCOUNT_ID) {
        return {
          ...next,
          channels: {
            ...next.channels,
            telecli: {
              ...next.channels?.telecli,
              enabled: true,
              ...(input.cliPath ? { telePath: input.cliPath } : {}),
            },
          },
        };
      }
      return {
        ...next,
        channels: {
          ...next.channels,
          telecli: {
            ...next.channels?.telecli,
            enabled: true,
            accounts: {
              ...next.channels?.telecli?.accounts,
              [accountId]: {
                ...next.channels?.telecli?.accounts?.[accountId],
                enabled: true,
                ...(input.cliPath ? { telePath: input.cliPath } : {}),
              },
            },
          },
        },
      };
    },
  },
  outbound: {
    deliveryMode: "direct",
    chunker: (text, limit) => getTeleCliRuntime().channel.text.chunkText(text, limit),
    chunkerMode: "text",
    textChunkLimit: 4000,
    sendText: async ({ to, text, accountId }) => {
      const result = await sendMessageTeleCli(to, text, {
        accountId: accountId ?? undefined,
      });
      return {
        channel: "telecli" as const,
        ...result,
      };
    },
    sendMedia: async ({ to, text, mediaUrl, accountId }) => {
      const media = mediaUrl?.trim() ?? "";
      const isLocalFile =
        media.startsWith("/") ||
        media.startsWith("./") ||
        media.startsWith("../") ||
        media.startsWith("file://");
      const filePath = isLocalFile ? (media.startsWith("file://") ? media.slice("file://".length) : media) : "";
      const merged = [text?.trim() ?? "", !isLocalFile ? media : ""].filter(Boolean).join("\n\n");
      const result = await sendMessageTeleCli(to, merged, {
        accountId: accountId ?? undefined,
        ...(filePath ? { file: [filePath] } : {}),
      });
      return {
        channel: "telecli" as const,
        ...result,
      };
    },
  },
  status: {
    defaultRuntime: {
      accountId: DEFAULT_ACCOUNT_ID,
      running: false,
      connected: false,
      lastStartAt: null,
      lastStopAt: null,
      lastError: null,
    },
    collectStatusIssues: (accounts) =>
      accounts.flatMap((account) => {
        const lastError = typeof account.lastError === "string" ? account.lastError.trim() : "";
        if (!lastError) {
          return [];
        }
        return [
          {
            channel: "telecli",
            accountId: account.accountId,
            kind: "runtime" as const,
            message: `Channel error: ${lastError}`,
          },
        ];
      }),
    buildChannelSummary: ({ snapshot }) => ({
      configured: snapshot.configured ?? false,
      running: snapshot.running ?? false,
      connected: snapshot.connected ?? false,
      lastStartAt: snapshot.lastStartAt ?? null,
      lastStopAt: snapshot.lastStopAt ?? null,
      lastError: snapshot.lastError ?? null,
    }),
    buildAccountSnapshot: ({ account, runtime, probe }) => ({
      accountId: account.accountId,
      name: account.name,
      enabled: account.enabled,
      configured: account.configured,
      telePath: account.telePath,
      session: account.session,
      daemonSession: account.daemonSession,
      sendSession: account.sendSession,
      configFile: account.configFile,
      sessionIsolate: account.config.sessionIsolate,
      ignorePeerIds: account.config.ignorePeerIds,
      dropWhenSelfOnline: account.config.dropWhenSelfOnline,
      running: runtime?.running ?? false,
      connected: runtime?.connected ?? false,
      lastStartAt: runtime?.lastStartAt ?? null,
      lastStopAt: runtime?.lastStopAt ?? null,
      lastError: runtime?.lastError ?? null,
      lastInboundAt: runtime?.lastInboundAt ?? null,
      lastOutboundAt: runtime?.lastOutboundAt ?? null,
      probe,
    }),
  },
  gateway: {
    startAccount: async (ctx) => {
      ctx.setStatus({
        accountId: ctx.account.accountId,
        connected: false,
      });
      ctx.log?.info(`[${ctx.account.accountId}] starting tele-cli daemon monitor`);
      return monitorTeleDaemon({
        accountId: ctx.account.accountId,
        config: ctx.cfg,
        runtime: ctx.runtime,
        abortSignal: ctx.abortSignal,
        statusSink: (patch) => ctx.setStatus({ accountId: ctx.account.accountId, ...patch }),
      });
    },
  },
};
