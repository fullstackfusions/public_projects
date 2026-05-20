# docker_compose

Reference `docker-compose.yml` showing a multi-service Kafka stack (Zookeeper + Kafka + Kafdrop UI + two app services) and the YAML anchor pattern (`x-common-service`) for reusing build/volume/env config across services.

The `Dockerfile` is intentionally empty — fill it in with the runtime for your `app_1` / `app_2` services (e.g. a Python or Node base image).

## Files

| File | Purpose |
|------|---------|
| `docker_compose.yml` | Multi-service compose definition with Kafka, Kafdrop, and two example app services using a shared anchor. |
| `Dockerfile` | Empty scaffold — supply your own base image and build steps. |

## Required environment

The compose file pulls `${vault_username}` and `${vault_password}` from a `.env` file at the project root:

```bash
echo "vault_username=youruser" > .env
echo "vault_password=yourpass" >> .env
```

App services also expect a second env file `.env.second`.

## Run

```bash
docker compose -f docker_compose.yml up -d
# Kafdrop UI: http://localhost:9000
# Kafka:      localhost:9092
```

## Notes

This is a teaching scaffold. For a fully working Kafka stack with producer/consumer code, see `kafka_kafdrop_ui_project/`.
