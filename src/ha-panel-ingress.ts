import {
  HomeAssistant,
  CustomPanelProperties,
  PanelInfo,
  navigate,
  ensureHaPanel,
} from "./ha-interfaces";
import { enableSidebarSwipe } from "./hass-sidebar-swipe";
import { mdiCoffeeOutline } from "@mdi/js";

// hassio addon ingress
interface HassioAddonDetails {
  ingress_url: string | null;
}

const fetchHassioAddonInfo = async (
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
  // document.cookie = `ingress_session=${session};path=/api/ingress/;SameSite=Strict${
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

const getHassioAddonUrl = async (
  elem: HTMLElement,
  hass: HomeAssistant,
  addonSlug: string,
  _baseUrl: string
): Promise<string | undefined> => {
  const showError = (msg: string): undefined => {
    (elem.shadowRoot || elem).innerHTML = `<pre>${msg}</pre>`;
  };

  const addon = await fetchHassioAddonInfo(hass, addonSlug);
  if (!addon) {
    return showError(`Unable to fetch add-on info of '${addonSlug}'`);
  }
  if (!addon.ingress_url) {
    return showError(`Add-on '${addonSlug}' does not support Ingress`);
  }
  // const targetUrl = baseUrl + addon.ingress_url.replace(/^\/api\/hassio_ingress(\/[^/]+).*/, "$1");
  const targetUrl = addon.ingress_url.replace(/\/+$/, "");

  let session: string;
  const obj = elem as { _sessionKeepAlive?: number };
  if (obj._sessionKeepAlive) {
    clearInterval(obj._sessionKeepAlive);
  }
  try {
    session = await createHassioSession(hass);
  } catch (err) {
    return showError(`Unable to create an Ingress session`);
  }
  obj._sessionKeepAlive = window.setInterval(async () => {
    try {
      await validateHassioSession(hass, session);
    } catch (err) {
      session = await createHassioSession(hass);
    }
  }, 60000);

  return targetUrl;
};

// hass ingress panel
interface IngressPanelUrlInfo {
  match: string;
  replace: string;
  default: string;
}

interface IngressPanelConfig {
  children?: Record<string, IngressPanelConfig>;
  title?: string;
  url?: string | IngressPanelUrlInfo;
  index?: string;
  addon?: string;
  token?: { value: string };
  ui_mode?: string;
}

class HaPanelIngress extends HTMLElement {
  private _setProperties?: (props: CustomPanelProperties) => void;
  private _panelPath: string = "";

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  async setProperties(props: CustomPanelProperties) {
    if (this._setProperties) {
      this._setProperties(props);
    }

    const config = this._getPanelConfig(props);
    if (!config) {
      return;
    }

    const targetUrl = await this._getTargetUrl(config, props);
    if (!targetUrl) {
      return;
    }

    await this._createIngressView(targetUrl, config, props);
  }

  private _getPanelConfig(props: CustomPanelProperties) {
    if (!props.panel && props.route) {
      props.panel = props.hass?.panels?.[props.route.prefix.slice(1)];
    }
    if (!props.panel) {
      return;
    }

    const panel = props.panel as PanelInfo<IngressPanelConfig>;
    let { config, title, url_path: panelPath } = panel;
    if (config.children) {
      const page = (props.route?.path || "").split("/")[1];
      if (page && Object.hasOwn(config.children, page)) {
        config = config.children[page];
        panelPath = `${panelPath}/${page}`;
      }
    } else {
      config.title = title || "";
    }

    if (this._panelPath === panelPath) {
      return;
    }
    this._panelPath = panelPath;
    return config;
  }

  private async _getTargetUrl(config: IngressPanelConfig, props: CustomPanelProperties) {
    let targetUrl = "";
    const urlParams = new URLSearchParams(window.location.search);
    const { url: urlInfo, addon: addonSlug } = config;
    const isIngress = urlInfo === undefined;
    if (typeof urlInfo === "object") {
      const { match, replace } = urlInfo;
      targetUrl = urlInfo["default"];
      if (match) {
        const origin = window.location.origin;
        const url = origin.replace(new RegExp(`^${match}$`, "i"), replace);
        if (origin !== url) {
          targetUrl = url;
        }
      }
    } else if (isIngress) {
      targetUrl = `/api/ingress/${config.token!.value}`;
      if (addonSlug) {
        const url = await getHassioAddonUrl(this, props.hass!, addonSlug, targetUrl);
        if (!url) {
          return;
        }
        targetUrl = url;
      }
    } else {
      targetUrl = urlInfo;
    }

    let { index } = config;
    if (index !== undefined) {
      const path = urlParams.get("index");
      if (path && !/(^|\/)\.\.\//.test(path)) {
        index = path.replace(/^\/+/, "");
      }
      targetUrl = `${targetUrl}/${index}`;
    }
    if (config.token && !isIngress) {
      const url = new URL(targetUrl);
      url.searchParams.set("ingressToken", config.token.value);
      targetUrl = url.href;
    }

    if (urlParams.has("replace")) {
      window.location.href = targetUrl;
    } else if (config.ui_mode === "replace") {
      if (targetUrl.indexOf("://") !== -1) {
        window.location.href = targetUrl;
      }
      navigate(targetUrl, { replace: true });
    } else {
      return targetUrl;
    }
  }

  private async _createIngressView(
    targetUrl: string,
    config: IngressPanelConfig,
    props: CustomPanelProperties
  ) {
    const { title } = config;
    let html = `
<iframe ${title ? `title="${title}"` : ""} src="${targetUrl}" allow="fullscreen"></iframe>
`;
    let css = `
  iframe {
    border: 0;
    width: 100%;
    height: 100%;
    display: block;
    background-color: var(--primary-background-color);
  }
`;

    const showToolbar = config.ui_mode === "toolbar";
    if (/*!showToolbar &&*/ enableSidebarSwipe()) {
      html += '<div id="swipebar"></div>';
      css += `
  #swipebar {
    position: fixed;
    top: 0;
    width: 20px;
    height: 100%;
  }
`;
    }

    if (showToolbar) {
      await ensureHaPanel("iframe");
      html = `<hass-subpage main-page>${html}
<ha-icon-button slot="toolbar-icon"></ha-icon-button>
</hass-subpage>`;
    }

    const root = this.shadowRoot as ShadowRoot;
    root.innerHTML = `<style>${css}</style>${html}`;
    if (showToolbar) {
      const subpage = root.querySelector("hass-subpage") as any;
      subpage.header = title;
      this._setProperties = (props) => {
        for (const k of ["hass", "narrow"]) {
          if (k in props) {
            subpage[k] = props[k as keyof typeof props];
          }
        }
      };
      this._setProperties(props);
      this._setButtons(subpage);
    }
  }

  private _setButtons(page: Element) {
    for (const [index, button] of page.querySelectorAll("ha-icon-button").entries()) {
      switch (index) {
        case 0: {
          (button as any).label = "Donate";
          (button as any).path = mdiCoffeeOutline;
          button.addEventListener("click", () => {
            const link = document.createElement("a");
            link.href = "https://buymeacoffee.com/lovelylain";
            link.target = "_blank";
            link.rel = "noreferrer";
            link.click();
          });
          break;
        }
      }
    }
  }
}

customElements.define("ha-panel-ingress", HaPanelIngress);
