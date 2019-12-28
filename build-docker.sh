#!/bin/bash

#DOCKER_REPO=lnr0626
DOCKER_REPO=td22057

TAG=$(jq -r '.version' ./hassio/config.json)

docker run --rm --privileged \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v ~/.docker:/root/.docker \
    -v "$(pwd)":/docker \
    hassioaddons/build-env:latest  \
    --all \
    -l \
    --from "homeassistant/{arch}-base" \
    --doc-url "https://github.com/TD22057/insteon-mqtt" \
    --name "Insteon MQTT" \
    --description "Insteon PLM <--> MQTT Bridge" \
    --image ${DOCKER_REPO}/{arch}-insteon-mqtt \
    --squash \
    --version ${TAG}

docker push ${DOCKER_REPO}/i386-insteon-mqtt
docker push ${DOCKER_REPO}/i386-insteon-mqtt:$TAG
docker push ${DOCKER_REPO}/armhf-insteon-mqtt
docker push ${DOCKER_REPO}/armhf-insteon-mqtt:$TAG
docker push ${DOCKER_REPO}/amd64-insteon-mqtt
docker push ${DOCKER_REPO}/amd64-insteon-mqtt:$TAG
docker push ${DOCKER_REPO}/aarch64-insteon-mqtt:$TAG
docker push ${DOCKER_REPO}/aarch64-insteon-mqtt
