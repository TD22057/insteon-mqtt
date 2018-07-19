#!/bin/bash

docker run --rm --privileged \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v ~/.docker:/root/.docker \
    -v "$(pwd)":/docker \
    hassioaddons/build-env:latest  \
    --all \
    -l \
    --from "homeassistant/{arch}-base" \
    --doc-url "https://github.com/TD22057/insteon-mqtt"

TAG=$(jq -r '.version' ./config.json)

docker push lnr0626/i386-insteon-mqtt
docker push lnr0626/i386-insteon-mqtt:$TAG
docker push lnr0626/armhf-insteon-mqtt
docker push lnr0626/armhf-insteon-mqtt:$TAG
docker push lnr0626/amd64-insteon-mqtt
docker push lnr0626/amd64-insteon-mqtt:$TAG
docker push lnr0626/aarch64-insteon-mqtt:$TAG
docker push lnr0626/aarch64-insteon-mqtt
