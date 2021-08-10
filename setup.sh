#!/bin/bash
cd container_bridge_c
docker-compose build
cd ../container_bridge_py
docker-compose build
