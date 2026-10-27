build-up:
	docker network create fastapi_net || true
	docker compose -f docker/psql/docker-compose.local.yaml up -d
	docker compose -f docker/rabbitmq/docker-compose.local.yaml up -d
	docker compose -f docker/kafka/docker-compose.local.yaml up -d
	docker compose -f docker/api/docker-compose.local.yaml up -d


