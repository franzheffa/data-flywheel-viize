#!/bin/bash

# MongoDB logs too noisy
docker compose -f ./deploy/docker-compose.yaml down && docker compose -f ./deploy/docker-compose.yaml up -d --build --no-attach mongodb
