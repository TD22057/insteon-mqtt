#!/bin/bash

docker run --rm --privileged \
  -v ~/.docker:/root/.docker \
  homeassistant/amd64-builder --all \
  -r https://github.com/TD22057/insteon-mqtt \
  -b master
