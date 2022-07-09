class IngressPanel extends HTMLElement {
  set panel(panel) {
    let config = panel.config;
    if (config.sub) {
      const page = window.location.pathname.split('/').pop();
      if (config.sub.hasOwnProperty(page)) {
        config = config.sub[page];
      }
    }
    window.location.href = `/api/ingress/${config.token}/${config.index}`;
  }
}
customElements.define("ingress-panel", IngressPanel);
