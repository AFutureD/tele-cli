import type { PluginRuntime } from "openclaw/plugin-sdk";

let runtime: PluginRuntime | null = null;

export function setTeleCliRuntime(next: PluginRuntime): void {
  runtime = next;
}

export function getTeleCliRuntime(): PluginRuntime {
  if (!runtime) {
    throw new Error("Tele CLI runtime not initialized");
  }
  return runtime;
}
