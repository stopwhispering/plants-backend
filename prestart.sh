#! /usr/bin/env bash

# Let the DB start
sleep 2;
# Run migrations
alembic upgrade head
