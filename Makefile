ENV_FILE := $(CURDIR)/.env
COMPOSE := docker compose --env-file $(ENV_FILE)
KEYCLOAK_COMPOSE := $(COMPOSE) -f docker/keycloak/docker-compose-base.yaml -f docker/keycloak/docker-compose-local.yaml

.PHONY: docker-build docker-up docker-down docker-up-keycloak docker-down-keycloak

# Keycloak itself is NOT part of the default stack: a shared instance
# already runs out-of-band (container `keycloak` on the external
# `shared_network`, from a sibling project) and that's what KEYCLOAK_SERVER_URL
# in .env points at. Use docker-up-keycloak/docker-down-keycloak only if you
# need price-hub's own standalone Keycloak instead (e.g. that shared one isn't
# running on this machine) — then also point KEYCLOAK_SERVER_URL at it.

docker-build:
	docker network create fastapi_net || true
	docker network create shared_network || true
	$(COMPOSE) -f docker/psql/docker-compose.local.yaml build
	$(COMPOSE) -f docker/rabbitmq/docker-compose.local.yaml build
	$(COMPOSE) -f docker/kafka/docker-compose.local.yaml build
	$(COMPOSE) -f docker/minio/docker-compose.local.yaml build
	$(COMPOSE) -f docker/redis/docker-compose.local.yaml build
	$(COMPOSE) -f docker/api/docker-compose.local.yaml build --no-cache

docker-up:
	docker network create fastapi_net || true
	docker network create shared_network || true
	$(COMPOSE) -f docker/psql/docker-compose.local.yaml up -d
	$(COMPOSE) -f docker/rabbitmq/docker-compose.local.yaml up -d
	$(COMPOSE) -f docker/kafka/docker-compose.local.yaml up -d
	$(COMPOSE) -f docker/minio/docker-compose.local.yaml up -d
	$(COMPOSE) -f docker/redis/docker-compose.local.yaml up -d
	$(COMPOSE) -f docker/api/docker-compose.local.yaml up -d

docker-down:
	$(COMPOSE) -f docker/api/docker-compose.local.yaml down
	$(COMPOSE) -f docker/psql/docker-compose.local.yaml down
	$(COMPOSE) -f docker/rabbitmq/docker-compose.local.yaml down
	$(COMPOSE) -f docker/kafka/docker-compose.local.yaml down
	$(COMPOSE) -f docker/minio/docker-compose.local.yaml down
	$(COMPOSE) -f docker/redis/docker-compose.local.yaml down

docker-up-keycloak:
	docker network create shared_network || true
	$(KEYCLOAK_COMPOSE) up -d --build

docker-down-keycloak:
	$(KEYCLOAK_COMPOSE) down
