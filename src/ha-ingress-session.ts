import { HomeAssistant } from "./ha-interfaces";

const setIngressCookie = (session: string): string => {
  document.cookie = `ha_ingress_session=${session};path=/api/ingress/;SameSite=Strict${
    location.protocol === "https:" ? ";Secure" : ""
  }`;
  return session;
};

const createIngressSession = async (hass: HomeAssistant): Promise<string> => {
  const resp: { session: string } = await hass.callWS({
    type: "ha-ingress/session",
  });
  return setIngressCookie(resp.session);
};

const validateIngressSession = async (hass: HomeAssistant, session: string) => {
  await hass.callWS({
    type: "ha-ingress/validate_session",
    session,
  });
  setIngressCookie(session);
};

// hassio ingress session manager
declare global {
  interface Window {
    __haIngressSession: {
      session: string;
      init(hass: HomeAssistant): Promise<boolean>;
    };
  }
}

export let haIngressSession = window.__haIngressSession;
if (!haIngressSession) {
  const resetState = (): {
    session: string;
    hass?: HomeAssistant;
    timer?: number;
  } => ({
    session: "",
  });
  let state = resetState();

  haIngressSession = window.__haIngressSession = {
    get session(): string {
      return state.session;
    },

    async init(hass: HomeAssistant): Promise<boolean> {
      if (!hass) return false;
      state.hass = hass;
      if (state.timer === undefined) {
        try {
          state.session = await createIngressSession(hass);
        } catch (err) {
          return false;
        }
        if (state.timer === undefined) {
          state.timer = setInterval(async () => {
            const hass = state.hass as HomeAssistant;
            try {
              await validateIngressSession(hass, state.session);
            } catch (err) {
              state.session = await createIngressSession(hass);
            }
          }, 60000);
        }
      }
      return true;
    },
  };
}
