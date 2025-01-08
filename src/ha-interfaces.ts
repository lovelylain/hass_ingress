export interface SidebarSwipeConfig {
  start_threshold?: number;
  end_threshold?: number;
  back_threshold?: number;
  prevent_others?: boolean;
  lock_vertical_scroll?: boolean;
  exclusions?: string[];
}

interface Lovelace {
  config: { sidebar_swipe: SidebarSwipeConfig | undefined } | undefined;
}

export interface HaPanelLovelace extends HTMLElement {
  lovelace: Lovelace | undefined;
}

export interface PanelInfo<T = Record<string, any> | null> {
  component_name: string;
  config: T;
  icon: string | null;
  title: string | null;
  url_path: string;
}

export interface HomeAssistant {
  callWS<T>(msg: Record<string, any>): Promise<T>;
  panels: Record<string, PanelInfo>;
}

export interface CustomPanelProperties {
  panel?: PanelInfo;
  hass?: HomeAssistant;
  narrow?: boolean;
  route?: {
    prefix: string;
    path: string;
  };
}

interface NavigateOptions {
  replace?: boolean;
  data?: any;
}

export const navigate = (path: string, options?: NavigateOptions) => {
  (document.createElement("ha-panel-custom") as any).navigate(path, options);
};

export const ensureHaElem = async (name: string, panel: string) => {
  if (!customElements.get(name)) {
    const panels = [{ url_path: "tmp", component_name: panel }];
    const ppr = document.createElement("partial-panel-resolver") as any;
    await (ppr._getRoutes || ppr.getRoutes).call(ppr, panels).routes.tmp.load();
  }
};
