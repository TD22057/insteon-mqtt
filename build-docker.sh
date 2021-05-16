#!/bin/bash

docker run --rm --privileged \
  -v ~/.docker:/root/.docker \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  homeassistant/amd64-builder \
  --all -r https://github.com/TD22057/insteon-mqtt -b master
