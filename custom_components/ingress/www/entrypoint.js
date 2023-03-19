class IngressPanel extends HTMLElement {
  set panel(panel) {
    let config = panel.config
    if (config.children) {
      const page = window.location.pathname.split('/').pop()
      if (config.children.hasOwnProperty(page)) {
        config = config.children[page]
      }
    }
    if (config.url) {
      window.location.href = config.url
    } else {
      window.location.href = `/api/ingress/${config.token.value}/${config.index}`
    }
  }
}
customElements.define("ingress-panel", IngressPanel)
