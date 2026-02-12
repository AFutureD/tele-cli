import { resolveTeleCliAccount } from "./accounts.js";
import { getTeleCliRuntime } from "./runtime.js";
import { getTeleDaemonRpcClient } from "./rpc.js";

export type TeleCliSendOpts = {
  accountId?: string;
  telePath?: string;
  session?: string;
  configFile?: string;
  timeoutMs?: number;
};

export type TeleCliSendResult = {
  messageId: string;
  to: string;
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

function isNumericPeerId(value: string): boolean {
  return /^-?\d+$/.test(value.trim());
}

function resolveAccount(opts: TeleCliSendOpts): ReturnType<typeof resolveTeleCliAccount> {
  const runtime = getTeleCliRuntime();
  const cfg = runtime.config.loadConfig();
  return resolveTeleCliAccount({
    cfg,
    accountId: opts.accountId,
  });
}

export async function sendMessageTeleCli(
  to: string,
  text: string,
  opts: TeleCliSendOpts = {},
): Promise<TeleCliSendResult> {
  const runtime = getTeleCliRuntime();
  const account = resolveAccount(opts);
  const target = to.trim();
  if (!target) {
    throw new Error("Tele CLI target is required");
  }

  const telePath = opts.telePath?.trim() || account.telePath;
  const session = opts.session ?? account.sendSession ?? account.session;
  const configFile = opts.configFile ?? account.configFile;
  const rpcClient = getTeleDaemonRpcClient(account.accountId);

  if (rpcClient) {
    await rpcClient.sendMessage({
      receiver: target,
      message: text ?? "",
      ...(isNumericPeerId(target) ? { entityType: "peer_id" as const } : {}),
    });
    runtime.channel.activity.record({
      channel: "telecli",
      accountId: account.accountId,
      direction: "outbound",
    });
    return {
      messageId: `tele-rpc-${Date.now()}`,
      to: target,
    };
  }

  const argv = [
    telePath,
    ...buildGlobalArgs({ session, configFile }),
    "message",
    "send",
  ];
  if (isNumericPeerId(target)) {
    argv.push("--entity", "peer_id");
  }
  argv.push(target, text ?? "");

  const result = await runtime.system.runCommandWithTimeout(argv, {
    timeoutMs: opts.timeoutMs ?? 30_000,
  });
  if (result.code !== 0) {
    const details = result.stderr.trim() || result.stdout.trim() || `exit code ${result.code ?? -1}`;
    throw new Error(`tele-cli send failed: ${details}`);
  }

  runtime.channel.activity.record({
    channel: "telecli",
    accountId: account.accountId,
    direction: "outbound",
  });

  return {
    messageId: `tele-${Date.now()}`,
    to: target,
  };
}
