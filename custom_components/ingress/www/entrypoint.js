{
class HaPanelIngress extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: 'open'});
  }

  setProperties(props) {
    if (this._setProperties) {
      this._setProperties(props);
    }

    if (!props.panel && props.route) {
      props.panel = props.hass?.panels?.[props.route.prefix.slice(1)];
    }
    if (!props.panel) {
      return;
    }

    let {config, title, url_path:panelPath} = props.panel;
    if (config.children) {
      const page = (props.route?.path || '').split('/')[1];
      if (page && config.children.hasOwnProperty(page)) {
        config = config.children[page];
        title = config.title;
        panelPath = `${panelPath}/${page}`;
      }
    }
    if (this._panelPath === panelPath) {
      return;
    }
    this._panelPath = panelPath;

    let {url:targetUrl, index} = config;
    if (typeof targetUrl === 'object') {
      const {match, replace} = targetUrl;
      targetUrl = targetUrl['default'];
      if (match) {
        const origin = window.location.origin;
        const url = origin.replace(new RegExp(`^${match}$`, 'i'), replace);
        if (origin !== url) {
          targetUrl = url;
        }
      }
    }

    const urlParams = new URLSearchParams(window.location.search);
    const isIngress = targetUrl === undefined;
    if (isIngress) targetUrl = `/api/ingress/${config.token.value}`;
    if (index !== undefined) {
      const path = urlParams.get('index');
      if (path && !/(^|\/)\.\.\//.test(path)) {
        index = path.replace(/^\/+/, '');
      }
      targetUrl = `${targetUrl}/${index}`;
    }
    if (config.token && !isIngress) {
      const url = new URL(targetUrl);
      url.searchParams.set('ingressToken', config.token.value);
      targetUrl = url.href;
    }

    if (urlParams.has('replace')) {
      window.location.href = targetUrl;
    } else if (config.ui_mode === 'replace') {
      if (targetUrl.indexOf('://') !== -1) {
        window.location.href = targetUrl;
      }
      document.createElement('ha-panel-custom').navigate(targetUrl, {replace: true});
    }
    const showToolbar = config.ui_mode === 'toolbar';

    let html = `
<iframe ${title ? `title="${title}"` : ''} src="${targetUrl}" allow="fullscreen"></iframe>
`;
    html = `
<style>
  iframe {
    border: 0;
    width: 100%;
    height: 100%;
    display: block;
    background-color: var(--primary-background-color);
  }
</style>
${showToolbar ? `<hass-subpage main-page>${html}</hass-subpage>` : html}
`;

    let func = (elem) => { elem.shadowRoot.innerHTML = html; };
    if (showToolbar) {
      const then = func;
      func = (elem) => {
        then(elem);
        const subpage = elem.shadowRoot.querySelector('hass-subpage');
        subpage.header = title;
        elem._setProperties = (props) => {
          for (const k of ['hass', 'narrow']) {
            if (props.hasOwnProperty(k)) {
              subpage[k] = props[k];
            }
          }
        };
        elem._setProperties(props);
      };
      if (!customElements.get('ha-panel-iframe')) {
        const then = func;
        func = (elem) => {
          const panels = [{url_path: 'tmp', component_name: 'iframe'}];
          const ppr = document.createElement('partial-panel-resolver');
          ppr.getRoutes(panels).routes.tmp.load().then(() => { then(elem); });
        };
      }
    }
    func(this);
  }
}
customElements.define('ha-panel-ingress', HaPanelIngress)
}
