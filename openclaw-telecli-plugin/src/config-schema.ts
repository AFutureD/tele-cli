import type { ChannelConfigSchema } from "openclaw/plugin-sdk";

type TeleCliPolicy = "open" | "pairing" | "disabled";
type TeleCliGroupPolicy = "open" | "allowlist" | "disabled";

export type TeleCliAccountConfig = {
  name?: string;
  capabilities?: string[];
  enabled?: boolean;
  configWrites?: boolean;
  telePath?: string;
  session?: string;
  daemonSession?: string;
  sendSession?: string;
  configFile?: string;
  dmPolicy?: TeleCliPolicy;
  allowFrom?: Array<string | number>;
  groupAllowFrom?: Array<string | number>;
  groupPolicy?: TeleCliGroupPolicy;
  textChunkLimit?: number;
  chunkMode?: "length" | "newline";
  blockStreaming?: boolean;
  responsePrefix?: string;
  sessionIsolate?: boolean;
  ignorePeerIds?: Array<string | number>;
};

export type TeleCliConfig = TeleCliAccountConfig & {
  accounts?: Record<string, TeleCliAccountConfig | undefined>;
};

const stringOrNumberArraySchema = {
  type: "array",
  items: {
    anyOf: [{ type: "string" }, { type: "number" }],
  },
} as const;

const accountSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    name: { type: "string" },
    capabilities: { type: "array", items: { type: "string" } },
    enabled: { type: "boolean" },
    configWrites: { type: "boolean" },
    telePath: { type: "string" },
    session: { type: "string" },
    daemonSession: { type: "string" },
    sendSession: { type: "string" },
    configFile: { type: "string" },
    dmPolicy: { type: "string", enum: ["open", "pairing", "disabled"] },
    allowFrom: stringOrNumberArraySchema,
    groupAllowFrom: stringOrNumberArraySchema,
    groupPolicy: { type: "string", enum: ["open", "allowlist", "disabled"] },
    textChunkLimit: { type: "integer", minimum: 1 },
    chunkMode: { type: "string", enum: ["length", "newline"] },
    blockStreaming: { type: "boolean" },
    responsePrefix: { type: "string" },
    sessionIsolate: { type: "boolean" },
    ignorePeerIds: stringOrNumberArraySchema,
  },
} as const;

export const teleCliChannelConfigSchema: ChannelConfigSchema = {
  schema: {
    ...accountSchema,
    properties: {
      ...accountSchema.properties,
      accounts: {
        type: "object",
        additionalProperties: accountSchema,
      },
    },
  },
};
