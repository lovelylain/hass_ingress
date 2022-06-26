class IngressPanel extends HTMLElement {
  set panel(panel) {
    window.location.href = `/api/ingress/${panel.config.token}/${panel.config.index}`;
  }
}
customElements.define("ingress-panel", IngressPanel);
