#!/bin/bash
docker compose up -d
flask --app server run --host localhost --debug
