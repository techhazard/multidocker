# Multidocker
run multiple compose files as one.

## Why? When? How? Whaaaa?
I'm using a reverse proxy container to make several containers available over HTTPS.
Because of this, the containers need to be in the same compose file.
After a while, the file started to grow out of control, so I wrote this tool to make it more manageable.


## Setup
### 1. Install multidocker
TODO: publish package on pypi
```sh
$ pip3 install multidocker
```

### 2. Setup directory
You will need the following setup:
```sh
$ tree
multidocker/
├── nextcloud/
│   └── docker-compose.yml
└── proxy/
    ├── docker-compose.yml
    ├── htpasswd
    ├── nginx-extra-options.conf
    └── vhost.d/
```

`nextcloud/docker-compose.yml`
```yml
---
version: '3.6'

# these two containers share the nextcloud
# network over which they will communicate
services:
  nextcloud:
    restart: unless-stopped
    image: nextcloud
    environment:
      VIRTUAL_HOST: "my_hostname.example.com"
      VIRTUAL_PORT: 80
      LETSENCRYPT_HOST: "my_hostname.example.com"
    volumes:
      - nextcloud_data:/var/www/html:rw
    # this adds the 'multidocker' network that allows
    # communication between compose files
    external: true
    networks:
      - nextcloud
    depends_on:
      - nextcloud_db

  nextcloud_db:
    restart: unless-stopped
    image: postgres:10.4
    environment:
      POSTGRES_PASSWORD: "secret"
      POSTGRES_USER: "nextcloud"
    volumes:
      - nextcloud_db:/var/lib/postgresql/data:rw
    networks:
      - nextcloud
...
```

`proxy/docker-compose.yml`
```yml
---
version: '3.6'
services:

  nginx:
    image: jwilder/nginx-proxy:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - nginx_conf:/etc/nginx/conf.d:rw
      - ./nginx-extra-options.conf:/etc/nginx/conf.d/extra.conf:ro
      - ./htpasswd:/etc/nginx/htpasswd_default:ro
      - ./vhost.d:/etc/nginx/vhost.d:ro
      - nginx_html:/usr/share/nginx/html:ro
      - nginx_dhparam:/etc/nginx/dhparam:rw
      - certificates:/etc/nginx/certs:ro
      - /var/run/docker.sock:/tmp/docker.sock:ro
    # this adds the 'multidocker' network that allows
    # communication between compose files
    external: true
    labels:
      - "com.github.jrcs.letsencrypt_nginx_proxy_companion.nginx_proxy"


  letsencrypt:
    image: jrcs/letsencrypt-nginx-proxy-companion
    volumes:
      - nginx_conf:/etc/nginx/conf.d:rw
      - nginx_vhost:/etc/nginx/vhost.d:rw
      - nginx_html:/usr/share/nginx/html:rw
      - certificates:/etc/nginx/certs:rw
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - nginx
...
```
(The other files are there for demonstration)

## Usage
You can use all the `docker-compose` commands: ps, up, down, logs etc.

### Single use
```sh
$ multidocker up -d
Creating network "multidocker_nextcloud_nextcloud" with the default driver
Creating network "multidocker_multidocker" with the default driver
Creating volume "multidocker_nextcloud_nextcloud_data" with default driver
Creating volume "multidocker_nextcloud_nextcloud_db" with default driver
Creating volume "multidocker_proxy_certificates" with default driver
Creating volume "multidocker_proxy_nginx_conf" with default driver
Creating volume "multidocker_proxy_nginx_dhparam" with default driver
Creating volume "multidocker_proxy_nginx_html" with default driver
Creating nextcloud_nextcloud_db ... done
Creating proxy_nginx            ... done
Creating nextcloud_nextcloud    ... done
```

### Interactive Mode
I've also added an interactive mode. You can start it by running `multidocker` without any arguments:
```sh
$ multidocker
Interactive Mode

You can run docker subcommands here, like so:
        ------------------------------------------
        | multidocker> ps                        |
        |     Name        Command  State   Ports |
        | ---------------------------------------|
        | container_name  /init    Up            |
        | multidocker>                           |
        ------------------------------------------

Commands:
  build              Build or rebuild services
  bundle             Generate a Docker bundle from the Compose file
  config             Validate and view the Compose file
  create             Create services
  down               Stop and remove containers, networks, images, and volumes
  events             Receive real time events from containers
  exec               Execute a command in a running container
  help               Get help on a command
  images             List images
  kill               Kill containers
  logs               View output from containers
  pause              Pause services
  port               Print the public port for a port binding
  ps                 List containers
  pull               Pull service images
  push               Push service images
  restart            Restart services
  rm                 Remove stopped containers
  run                Run a one-off command
  scale              Set number of containers for a service
  start              Start services
  stop               Stop services
  top                Display the running processes
  unpause            Unpause services
  up                 Create and start containers
  version            Show the Docker-Compose version information

Multidocker Commands:
  cat                Output combined compose file to disk
  help               Show this help text
  reload             Reload the compose files from disk
  write              Write the combined compsose file to disk
  quit, exit         Exit interactive mode (ctrl+d also works)
```
You can run all the docker-compose command from within this prompt. It saves you from having to type `multidocker` before each command.
It also saves time because it keeps the combined compose file in memory. If you changed one of the compose files, you should run the `reload`command.


## Improvements:
- [ ] Auto reload on file change
- [ ] Use readline in interactive mode
- [ ] Shell-like history in interactive mode
- [ ] Upgrade to python 3.7 to use the improved `subprocess.run`
