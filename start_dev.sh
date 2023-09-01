#!/bin/bash
docker compose up -d
flask --app analyst.server run --host localhost --debug
