import { DEFAULT_ACCOUNT_ID, normalizeAccountId, type OpenClawConfig } from "openclaw/plugin-sdk";
import type { TeleCliConfig } from "./config-schema.js";

export type ResolvedTeleCliAccount = {
  accountId: string;
  name?: string;
  enabled: boolean;
  configured: boolean;
  telePath: string;
  session?: string;
  daemonSession?: string;
  sendSession?: string;
  configFile?: string;
  config: {
    dmPolicy?: "open" | "pairing" | "disabled";
    allowFrom?: Array<string | number>;
    ignorePeerIds?: Array<string | number>;
    groupPolicy?: "open" | "allowlist" | "disabled";
    groupAllowFrom?: Array<string | number>;
    textChunkLimit?: number;
    chunkMode?: "length" | "newline";
    blockStreaming?: boolean;
    responsePrefix?: string;
    sessionIsolate?: boolean;
    dropWhenSelfOnline?: boolean;
  };
};

function readTeleCliConfig(cfg: OpenClawConfig): TeleCliConfig {
  return (cfg.channels?.telecli ?? {}) as TeleCliConfig;
}

export function listTeleCliAccountIds(cfg: OpenClawConfig): string[] {
  const teleCfg = readTeleCliConfig(cfg);
  const ids = new Set<string>([DEFAULT_ACCOUNT_ID]);
  for (const key of Object.keys(teleCfg.accounts ?? {})) {
    ids.add(normalizeAccountId(key));
  }
  return Array.from(ids.values());
}

export function resolveDefaultTeleCliAccountId(_cfg: OpenClawConfig): string {
  return DEFAULT_ACCOUNT_ID;
}

export function resolveTeleCliAccount(params: {
  cfg: OpenClawConfig;
  accountId?: string | null;
}): ResolvedTeleCliAccount {
  const teleCfg = readTeleCliConfig(params.cfg);
  const accountId = normalizeAccountId(params.accountId ?? DEFAULT_ACCOUNT_ID);
  const accountCfg = accountId === DEFAULT_ACCOUNT_ID ? teleCfg : teleCfg.accounts?.[accountId] ?? {};

  const channelEnabled = teleCfg.enabled !== false;
  const enabled = channelEnabled && accountCfg.enabled !== false;

  const telePath = (accountCfg.telePath ?? teleCfg.telePath ?? "tele").trim();
  const session = accountCfg.session ?? teleCfg.session;
  const daemonSession = accountCfg.daemonSession ?? teleCfg.daemonSession ?? session;
  const sendSession = accountCfg.sendSession ?? teleCfg.sendSession ?? session;
  const configFile = accountCfg.configFile ?? teleCfg.configFile;

  return {
    accountId,
    name: accountCfg.name,
    enabled,
    configured: telePath.length > 0,
    telePath,
    session,
    daemonSession,
    sendSession,
    configFile,
    config: {
      dmPolicy: accountCfg.dmPolicy ?? teleCfg.dmPolicy,
      allowFrom: accountCfg.allowFrom ?? teleCfg.allowFrom,
      ignorePeerIds: accountCfg.ignorePeerIds ?? teleCfg.ignorePeerIds,
      groupPolicy: accountCfg.groupPolicy ?? teleCfg.groupPolicy,
      groupAllowFrom: accountCfg.groupAllowFrom ?? teleCfg.groupAllowFrom,
      textChunkLimit: accountCfg.textChunkLimit ?? teleCfg.textChunkLimit,
      chunkMode: accountCfg.chunkMode ?? teleCfg.chunkMode,
      blockStreaming: accountCfg.blockStreaming ?? teleCfg.blockStreaming,
      responsePrefix: accountCfg.responsePrefix ?? teleCfg.responsePrefix,
      sessionIsolate: accountCfg.sessionIsolate ?? teleCfg.sessionIsolate,
      dropWhenSelfOnline: accountCfg.dropWhenSelfOnline ?? teleCfg.dropWhenSelfOnline,
    },
  };
}
