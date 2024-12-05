import { HomeAssistant } from "./ha-interfaces";

// hassio ingress api
interface HassioAddonDetails {
  ingress_url: string | null;
}

export const fetchHassioAddonInfo = async (
  hass: HomeAssistant,
  addonSlug: string
): Promise<HassioAddonDetails | null> => {
  let addon: HassioAddonDetails | null = null;
  try {
    addon = await hass.callWS({
      type: "supervisor/api",
      endpoint: `/addons/${addonSlug}/info`,
      method: "get",
    });
  } catch (err) {}
  return addon;
};

const createHassioSession = async (hass: HomeAssistant): Promise<string> => {
  const resp: { session: string } = await hass.callWS({
    type: "supervisor/api",
    endpoint: "/ingress/session",
    method: "post",
  });
  const session = resp.session;
  document.cookie = `ingress_session=${session};path=/api/hassio_ingress/;SameSite=Strict${
    location.protocol === "https:" ? ";Secure" : ""
  }`;
  return session;
};

const validateHassioSession = async (hass: HomeAssistant, session: string) => {
  await hass.callWS({
    type: "supervisor/api",
    endpoint: "/ingress/validate_session",
    method: "post",
    data: { session },
  });
};

// hassio ingress session manager
declare global {
  interface Window {
    __ingressSession: {
      session: string;
      refCount: number;
      init: (hass: HomeAssistant) => Promise<boolean>;
      fini: () => void;
    };
  }
}

export let ingressSession = window.__ingressSession;
if (!ingressSession) {
  const resetState = (): {
    session: string;
    refCount: number;
    hass?: HomeAssistant;
    timer?: number;
  } => ({
    session: "",
    refCount: 0,
  });
  let state = resetState();

  ingressSession = window.__ingressSession = {
    get session(): string {
      return state.session;
    },

    get refCount(): number {
      return state.refCount;
    },

    async init(hass: HomeAssistant): Promise<boolean> {
      if (!hass) return false;
      state.hass = hass;
      if (state.timer !== undefined) {
        ++state.refCount;
      } else {
        try {
          state.session = await createHassioSession(hass);
        } catch (err) {
          return false;
        }
        state.timer = window.setInterval(async () => {
          const hass = state.hass as HomeAssistant;
          try {
            await validateHassioSession(hass, state.session);
          } catch (err) {
            state.session = await createHassioSession(hass);
          }
        }, 60000);
        state.refCount = 1;
      }
      return true;
    },

    fini() {
      if (state.timer !== undefined) {
        if (--state.refCount <= 0) {
          clearInterval(state.timer);
          state = resetState();
        }
      }
    },
  };
}
