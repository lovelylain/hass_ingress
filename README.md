# hass_ingress

![GitHub actions](https://github.com/lovelylain/hass_ingress/actions/workflows/validate.yaml/badge.svg)

Hass.io provides a very nice feature called [Hass.io Ingress](https://www.home-assistant.io/blog/2019/04/15/hassio-ingress/), `hass_ingress` extracts this feature into a standalone integration, it allows you to add additional ingress panels to your Home Assistant frontend. The panels are listed in the sidebar and can contain external resources like the web frontend of your router, your monitoring system, or your media server. Home Assistant will take care of the authentication and the secure connection, so users can access the external resources without extra login.

![overview](images/overview.png)

## Features

- Ingress function similar to [Hass.io Ingress](https://www.home-assistant.io/blog/2019/04/15/hassio-ingress/). (option: `ingress: true`)
- Sidebar function similar to [Panel_iframe](https://www.home-assistant.io/integrations/panel_iframe/). (option: `ingress: false`)
- Add any HA page as a sidebar panel. (option: `ui_mode: replace`)
- Hide header on ingress panel pages. (option: `ui_mode: normal`)
- Show header on ingress panel pages. (option: `ui_mode: toolbar`)
- Hide ingress panels from sidebar. (option: `parent: parent_panel`)
- Additional http headers passed to the backend service, such as `authorization` and `host`, so that we can access the external resources without extra login.  (option: `ingress: true` `header: {map}`)
- Embed in other pages. (url: `/api/ingress/{name}/`)
- Passing url parameters. (url: `/{panel}?index={overwrite_index}`)
- Reload Ingress configuration without restarting HA.

## Install

You can install this custom component by adding this repository (https://github.com/lovelylain/hass_ingress) to HACS in the settings menu of HACS first. You will find the custom component in the integration menu afterwards, look for `Ingress`. Alternatively, you can install it manually by copying the custom_component folder to your Home Assistant configuration folder.

## Configuration

To enable Ingress panels in your installation, add the following to your `configuration.yaml` file, then restart HA:

```yaml
ingress:
  link_automation:
    ingress: false
    ui_mode: replace
    title: Automation
    icon: mdi:link
    url: /config/automation/dashboard
  frigate:
    ui_mode: toolbar
    title: Frigate
    icon: mdi:cctv
    url: http://172.30.32.2:5000
  nodered:
    require_admin: true
    title: Node-RED
    icon: mdi:sitemap
    url: http://127.0.0.1:45180
    headers:
      authorization: !secret nodered_auth
  nodered_ui:
    parent: nodered
    title: Node-RED Dashboard
    icon: mdi:monitor-dashboard
    url: http://127.0.0.1:45180
    index: /ui/
    headers:
      authorization: !secret nodered_auth
```

After you modify the Ingress configuration, you can go to `developer-tools` page and click `Reload Ingress` to reload without restarting HA.

![reload](images/reload.png)

## Configuration variables

- **ingress**: map (REQUIRED) Enables the hass_ingress integration. Only allowed once.
  - **panel_name**: map (REQUIRED) Name of the panel. Only allowed once.
    - **title**: string (REQUIRED) Friendly title for the panel. Will be used in the sidebar.
    - **icon**: [icon](https://www.home-assistant.io/docs/configuration/customizing-devices/#icon) (optional) Icon for entry.
    - **require_admin**: boolean (optional, default: false) If admin access is required to see this iframe.
    - **ingress**: boolean (optional, default: true) [Panel_iframe](https://www.home-assistant.io/integrations/panel_iframe/) mode if false else ingress mode.
    - **ui_mode**: string (oneof `replace` `normal` `toolbar`, default: normal)
      - replace: Redirect to the target url, useful when adding an HA page as a sidebar panel.
      - normal: No header on ingress panel pages.
      - toolbar: Show header on ingress panel pages. It is recommended to use toolbar instead of normal on HA versions higher than [2023.3.6](https://github.com/home-assistant/android/issues/3460).
    - **url**: string (REQUIRED) The absolute URL or relative URL with an absolute path to open.
    - **index**: string (optional, default empty) The relative URL of index page. If the `url` is http://127.0.0.1:45180/ui/, all access must be under the /ui/ path; if the `url` is http://127.0.0.1:45180 and the `index` is /ui/, all paths of http://127.0.0.1:45180 can be accessed.
    - **parent**: string (optional, default empty) Parent ingress panel name. If non-empty, this panel will be hidden from the HA sidebar and you can access it via the `/{parent panel_name}/{child panel_name}` link. For example, the parent panel `nodered`, the sub-panel `ui` or `nodered_ui`, you can access the sub-panel through `/nodered/ui`.
    - **headers**: map (optional) Additional http headers passed to the backend service, such as `authorization` for `basic auth`.
    - **expire_time**: integer (optional, default: 3600) Hass ingress generates a token for each panel, which is used to access the panel. This option is used to specify the token validity period.
    - **cookie_name**: string (optional, default: ingress_token) Hass ingress uses cookies to pass tokens, if the cookie name conflicts with the backend service, you can use other value through this option.
    - **disable_chunked**: boolean (optional, default: false) If the backend service does not support chunked encoding, you can disable chunked through this option.

*Notice: Not all backend services can be proxied by ingress, it must use relative paths or use `X-Ingress-Path` http header to generate correct absolute paths. For unsupported backend services, you can try to use nginx's sub_filter to fix the absolute paths in the response.*
