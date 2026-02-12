import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { emptyPluginConfigSchema } from "openclaw/plugin-sdk";
import { teleCliPlugin } from "./src/channel.js";
import { setTeleCliRuntime } from "./src/runtime.js";

const plugin = {
  id: "tele-cli",
  name: "Tele CLI",
  description: "Channel plugin backed by tele-cli daemon",
  configSchema: emptyPluginConfigSchema(),
  register(api: OpenClawPluginApi) {
    setTeleCliRuntime(api.runtime);
    api.registerChannel({ plugin: teleCliPlugin });
  },
};

export default plugin;
