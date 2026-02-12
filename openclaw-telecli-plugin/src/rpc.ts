export type TeleDaemonRpcSendMessageParams = {
  receiver: string;
  message: string;
  entityType?: "peer_id";
};

export type TeleDaemonRpcClient = {
  sendMessage: (params: TeleDaemonRpcSendMessageParams) => Promise<{ sent: boolean; receiver: string }>;
  close?: () => void;
};

const clients = new Map<string, TeleDaemonRpcClient>();

export function registerTeleDaemonRpcClient(accountId: string, client: TeleDaemonRpcClient): void {
  clients.set(accountId, client);
}

export function getTeleDaemonRpcClient(accountId: string): TeleDaemonRpcClient | null {
  return clients.get(accountId) ?? null;
}

export function unregisterTeleDaemonRpcClient(accountId: string): void {
  const client = clients.get(accountId);
  clients.delete(accountId);
  try {
    client?.close?.();
  } catch {
    // ignore cleanup errors
  }
}
