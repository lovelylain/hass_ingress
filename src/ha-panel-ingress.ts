import {
  HomeAssistant,
  CustomPanelProperties,
  PanelInfo,
  navigate,
  ensureHaElem,
} from "./ha-interfaces";
import { fetchHassioAddonInfo, ingressSession } from "./hassio-ingress";
import { enableSidebarSwipe } from "./hass-sidebar-swipe";
import { mdiCoffeeOutline } from "@mdi/js";

// hassio addon ingress
const getHassioAddonUrl = async (
  elem: HTMLElement,
  hass: HomeAssistant,
  addonSlug: string,
  dryRun?: boolean
): Promise<string | undefined> => {
  const showError = (msg: string): undefined => {
    if (!dryRun) (elem.shadowRoot || elem).innerHTML = `<pre>${msg}</pre>`;
  };

  const addon = await fetchHassioAddonInfo(hass, addonSlug);
  if (!addon) {
    return showError(`Unable to fetch add-on info of '${addonSlug}'`);
  }
  if (!addon.ingress_url) {
    return showError(`Add-on '${addonSlug}' does not support Ingress`);
  }
  const targetUrl = addon.ingress_url.replace(/\/+$/, "");

  if (!dryRun && !(await ingressSession.init(hass))) {
    return showError(`Unable to create an Ingress session`);
  }
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
  icon?: string;
  url?: string | IngressPanelUrlInfo;
  index?: string;
  addon?: string;
  token?: { value: string };
  ui_mode?: string;
}

class HaPanelIngress extends HTMLElement {
  private _setProperties?: (props: CustomPanelProperties) => void;
  private _panelPath: string = "";
  private _isHassio?: HomeAssistant;
  private _disconnected? = true;

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  public connectedCallback() {
    delete this._disconnected;
    if (this._isHassio) {
      ingressSession.init(this._isHassio);
    }
  }

  public disconnectedCallback() {
    this._disconnected = true;
    if (this._isHassio) {
      ingressSession.fini();
    }
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
    let { config, url_path: panelPath } = panel;
    config.title = panel.title!;
    config.icon = panel.icon!;
    if (config.children) {
      const page = (props.route?.path || "").split("/", 2)[1];
      if (page && page in config.children) {
        config = config.children[page];
        panelPath = `${panelPath}/${page}`;
      }
    }

    if (this._panelPath === panelPath) {
      return;
    }
    this._panelPath = panelPath;
    delete this._setProperties;
    return config;
  }

  private async _getTargetUrl(
    config: IngressPanelConfig,
    props: CustomPanelProperties,
    dryRun?: boolean
  ) {
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
        const url = await getHassioAddonUrl(this, props.hass!, addonSlug, dryRun);
        if (!url) {
          return;
        }
        targetUrl = url;
      }
    } else {
      targetUrl = urlInfo;
    }

    if (!dryRun) {
      if (this._isHassio) {
        ingressSession.fini();
        delete this._isHassio;
      }
      if (addonSlug) {
        this._isHassio = props.hass;
        if (this._disconnected) {
          ingressSession.fini();
        }
      }
    }

    let { index, ui_mode: uiMode } = config;
    if (index !== undefined) {
      const path = urlParams.get("index");
      if (!dryRun && path && !/(^|\/)\.\.\//.test(path)) {
        index = path.replace(/^\/+/, "");
      }
      targetUrl = `${targetUrl}/${index}`;
    }
    if (config.token && !isIngress) {
      const url = new URL(targetUrl);
      url.searchParams.set("ingressToken", config.token.value);
      targetUrl = url.href;
    }

    if (dryRun || uiMode === "custom") {
      return targetUrl;
    } else if (urlParams.has("replace")) {
      if (addonSlug) {
        targetUrl = `/files/ingress/iframe.html?ingress=${encodeURIComponent(targetUrl)}`;
      }
      window.location.href = targetUrl;
    } else if (uiMode === "replace") {
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
    const forwardProps = (elem: any, keys: string[]) => {
      if ("setProperties" in elem) {
        return elem.setProperties as (props: CustomPanelProperties) => void;
      } else {
        return (props: CustomPanelProperties) => {
          for (const k of keys) {
            if (k in props) elem[k] = props[k as keyof typeof props];
          }
        };
      }
    };

    const root = this.shadowRoot as ShadowRoot;
    const { ui_mode: uiMode, title, icon } = config;
    if (uiMode === "custom") {
      const children: Record<string, IngressPanelConfig> = {};
      for (const [k, c] of Object.entries(config.children || {})) {
        if (!c.title) continue;
        const url = await this._getTargetUrl(c, props, true);
        if (url) {
          const { title, icon, ui_mode } = c;
          children[k] = { url, title, icon, ui_mode };
        }
      }
      try {
        const { default: create } = await import(targetUrl);
        const elem = await create({ children, title, icon, ensureHaElem, ingressSession });
        if (!(elem instanceof HTMLElement)) {
          throw new Error("custom should export default async(config)=>HTMLElement");
        }
        root.innerHTML = "";
        root.appendChild(elem);
        this._setProperties = forwardProps(elem, ["hass", "narrow", "route"]);
        this._setProperties(props);
      } catch (e) {
        root.innerHTML = `<pre>custom url[${targetUrl}] is invalid:\n${e}</pre>`;
      }
      return;
    }

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

    const showToolbar = uiMode === "toolbar";
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
      await ensureHaElem("hass-subpage", "iframe");
      html = `<hass-subpage main-page>${html}
<ha-icon-button slot="toolbar-icon"></ha-icon-button>
</hass-subpage>`;
    }

    root.innerHTML = `<style>${css}</style>${html}`;
    if (showToolbar) {
      const subpage = root.querySelector("hass-subpage") as any;
      this._setButtons(subpage);
      subpage.header = title;
      this._setProperties = forwardProps(subpage, ["hass", "narrow"]);
      this._setProperties(props);
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
