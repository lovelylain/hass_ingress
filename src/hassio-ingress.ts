import { HomeAssistant } from "./ha-interfaces";

// hassio ingress api
interface HassioAddonDetails {
  ingress_url: string | null;
}

export const fetchHassioAddonInfo = async (
  hass: HomeAssistant,
  slug: string
): Promise<HassioAddonDetails | null> => {
  let addon: HassioAddonDetails | null = null;
  try {
    addon = await hass.callWS({
      type: "supervisor/api",
      endpoint: `/addons/${slug}/info`,
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
    finiTimer?: number;
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
      if (state.timer === undefined) {
        try {
          state.session = await createHassioSession(hass);
        } catch (err) {
          return false;
        }
        if (state.timer === undefined) {
          state.timer = setInterval(async () => {
            const hass = state.hass as HomeAssistant;
            try {
              await validateHassioSession(hass, state.session);
            } catch (err) {
              state.session = await createHassioSession(hass);
            }
          }, 60000);
          state.refCount = 0;
        }
      }
      ++state.refCount;
      return true;
    },

    fini() {
      if (state.timer !== undefined) {
        --state.refCount;
        clearTimeout(state.finiTimer);
        state.finiTimer = setTimeout(() => {
          delete state.finiTimer;
          if (state.refCount <= 0 && state.timer !== undefined) {
            clearInterval(state.timer);
            state = resetState();
          }
        }, 60000);
      }
    },
  };
}
