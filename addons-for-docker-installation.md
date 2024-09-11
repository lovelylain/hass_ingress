# Addons for Docker installation

This guide helps you run Home Assistant and addons(equivalent containers) in a container environment without hassio.

## Table of Contents

- [Overview](#overview)
- [Basic Environment](#basic-environment)
  - [Network](#network)
  - [DNS Proxy](#dns-proxy)
  - [Home Assistant](#home-assistant)
- [Addons](#addons)
  - [MQTT](#mqtt)
  - [VSCode](#vscode)
  - [Node-RED](#node-red)
  - [Zigbee2MQTT](#zigbee2mqtt)
  - To be continued
- [Other Services](#other-services)
  - [OpenWrt](#openwrt)
  - To be continued

## Overview

We use docker compose in order to maintain containers. For homeassistant access to addons, we put all containers in a custom bridge so they can be accessed via dns. Homeassistant requires the host network for functions such as dlna to work properly, so a dns proxy is introduced.

Here is an example run homeassistant and node-red:

```shell
mkdir -p /opt/hassio
cd /opt/hassio
vim docker-compose.yml  # see content below
mkdir nginx node-red
vim nginx/dns_proxy.conf  # see content below
chown 1000:1000 node-red
docker compose up -d
# Access http://local_ip:8123/ to configure homeassistant
# Install Ingress integration in homeassistant
vim homeassistant/configuration.yaml  # add content below
docker compose restart homeassistant
# Now you can access Node-RED from HA's sidebar. If you want add new addons,
#  add service in docker-compose.yml then `docker compose up -d`
#  add ingress in configuration.yaml then reload INGRESS.
```

docker-compose.yml:

```yaml
name: ha
networks:
  default:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.name: hassio
    ipam:
      config:
        - subnet: 172.30.32.0/23
          ip_range: 172.30.33.0/24
          gateway: 172.30.32.1
services:
  dns:
    image: nginx
    restart: always
    networks:
      default:
        ipv4_address: 172.30.32.3
    tty: true
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - ./nginx/dns_proxy.conf:/etc/nginx/nginx.conf
  homeassistant:
    image: homeassistant/home-assistant
    restart: always
    privileged: true
    network_mode: host
    dns:
      - 172.30.32.3
    dns_opt:
      - ndots:0
    tty: true
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - /run/dbus:/run/dbus:ro
      - ./homeassistant:/config
      - ./share:/share
  nodered:
    image: nodered/node-red
    restart: unless-stopped
    tty: true
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - ./node-red:/data
      - ./share:/share
  # add other services like nodered does
```

configuration.yaml:

```yaml
ingress:
  nodered:
    require_admin: true
    title: Node-RED
    icon: mdi:sitemap
    url: nodered:1880
  # add other ingress like nodered does
```

## Basic Environment

### Network

Create `./docker-compose.yml`.

docker-compose.yml:

```yaml
name: ha
networks:
  default:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.name: hassio
    ipam:
      config:
        - subnet: 172.30.32.0/23
          ip_range: 172.30.33.0/24
          gateway: 172.30.32.1
```

### DNS Proxy

Edit `./docker-compose.yml`, create `./nginx/dns_proxy.conf`, then run `docker compose up -d`.

docker-compose.yml:

```yaml
name: ha
services:
  dns:
    image: nginx
    restart: always
    networks:
      default:
        ipv4_address: 172.30.32.3
    tty: true
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - ./nginx/dns_proxy.conf:/etc/nginx/nginx.conf
```

dns_proxy.conf:

```c++
user  nginx;
worker_processes  1;

error_log  /var/log/nginx/error.log notice;
pid        /var/run/nginx.pid;

events {
    worker_connections  1024;
}

stream {
  log_format main '$remote_addr [$time_local] "$upstream_addr" $protocol '
                  '$status $bytes_sent $bytes_received $session_time';

  server {
    access_log /var/log/nginx/access.log main;
    listen 53 udp;
    proxy_pass 127.0.0.11:53;
    proxy_timeout 10s;
  }
}
```

### Home Assistant

Edit `./docker-compose.yml`, run `docker compose up -d`.
Then install [Ingress integration](https://github.com/lovelylain/hass_ingress#install), edit `./homeassistant/configuration.yaml`, run `docker compose restart homeassistant`.

docker-compose.yml:

```yaml
name: ha
services:
  homeassistant:
    image: homeassistant/home-assistant
    restart: always
    privileged: true
    network_mode: host
    dns:
      - 172.30.32.3
    dns_opt:
      - ndots:0
    tty: true
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - /run/dbus:/run/dbus:ro
      - ./homeassistant:/config
      - ./share:/share
```

configuration.yaml:

```yaml
ingress:
```

## Addons

### MQTT

Edit `./docker-compose.yml`, create `./mosquitto/{mosquitto.conf,pw,acl}`, then run `docker compose up -d`.

Refer to https://github.com/iegomez/mosquitto-go-auth#files for how to create `pw` and `acl` file.<br>
Refer to https://www.home-assistant.io/integrations/mqtt/ for how to configure MQTT in home-assistant.

docker-compose.yml:

```yaml
name: ha
services:
  mqtt:
    image: iegomez/mosquitto-go-auth
    restart: always
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - ./mosquitto:/etc/mosquitto
```

mosquitto.conf:

```python
##
# defaults
protocol mqtt
user mosquitto

##
# logging
log_dest stdout

##
# datastore
persistence true
persistence_location /etc/mosquitto/

##
# User settings
auth_plugin /mosquitto/go-auth.so
auth_opt_files_password_path /etc/mosquitto/pw
auth_opt_files_acl_path /etc/mosquitto/acl

listener 1883
```

### VSCode

Edit `./docker-compose.yml`, then run `docker compose up -d`.

Edit `./homeassistant/configuration.yaml` then reload `INGRESS`.

docker-compose.yml:

```yaml
name: ha
services:
  vscode:
    image: linuxserver/code-server
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
      - PUID=0
      - PGID=0
    volumes:
      - ./vscode:/config
      - .:/data
```

configuration.yaml:

```yaml
ingress:
  vscode:
    require_admin: true
    title: VSCode
    icon: mdi:microsoft-visual-studio-code
    url: vscode:8443
```

### Node-RED

Edit `./docker-compose.yml`, then run `docker compose up -d`, you may need run `sudo chown 1000:1000 -R ./node-red`.

Edit `./homeassistant/configuration.yaml` then reload `INGRESS`.

Refer to [node-red-contrib-home-assistant-websocket](https://zachowj.github.io/node-red-contrib-home-assistant-websocket/guide/#generate-access-token) for how to configure Node-RED with home-assistant.

docker-compose.yml:

```yaml
name: ha
services:
  nodered:
    image: nodered/node-red
    restart: unless-stopped
    tty: true
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - ./node-red:/data
      - ./share:/share
```

configuration.yaml:

```yaml
ingress:
  nodered:
    require_admin: true
    title: Node-RED
    icon: mdi:sitemap
    url: nodered:1880
```

### Zigbee2MQTT

Edit `./docker-compose.yml`, then run `docker compose up -d`.

Edit `./homeassistant/configuration.yaml` then reload `INGRESS`.

Refer to https://www.zigbee2mqtt.io/guide/configuration/ for how to configure Zigbee2MQTT.

docker-compose.yml:

```yaml
name: ha
services:
  zigbee2mqtt:
    image: koenkk/zigbee2mqtt
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - /run/udev:/run/udev:ro
      - ./zigbee2mqtt:/app/data
    devices:
      - /dev/ttyACM0
```

configuration.yaml:

```yaml
ingress:
  zigbee2mqtt:
    title: Zigbee2MQTT
    icon: mdi:zigbee
    url: zigbee2mqtt:8080
```

## Other Services

### OpenWrt

Edit `./homeassistant/configuration.yaml` then reload `INGRESS`.

configuration.yaml:

```yaml
ingress:
  openwrt:
    title: OpenWrt
    icon: mdi:router-wireless
    url: 192.168.0.1
    headers:
      # auto login for openwrt ingress
      http-auth-user: !secret openwrt_user
      http-auth-pass: !secret openwrt_auth
    # "fix" absolute URLs by rewriting the response body
    # also disable streaming, or it won't work
    disable_stream: True
    rewrite:
      # for HTML response
      - mode: body
        match: /(luci-static|cgi-bin)/
        replace: $http_x_ingress_path/\1/
      # for JS init code
      - mode: body
        match: \\/(luci-static|cgi-bin|ubus)\\/
        replace: $http_x_ingress_path\/\1\/
      # for login response
      - mode: header
        name: "(Location|Set-Cookie)"
        match: /cgi-bin/
        replace: $http_x_ingress_path/cgi-bin/
```
