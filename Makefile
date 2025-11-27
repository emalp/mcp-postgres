DOCKER ?= docker
IMAGE_NAME ?= database-debugger-mcp
IMAGE_TAG ?= latest
HOST_PORT ?= 8000
CONTAINER_PORT ?= 8000
MCP_HOST ?= 0.0.0.0

.PHONY: build docker-build run docker-run

# Build the Docker image for the MCP server.
build docker-build:
	$(DOCKER) build \
		-t $(IMAGE_NAME):$(IMAGE_TAG) \
		-f Dockerfile \
		.

# Run the newly built image with the recommended parameters.
run docker-run:
	@if [ -z "$(DATABASE_URL)" ]; then \
		echo "DATABASE_URL must be set (e.g., export DATABASE_URL=postgres://readonly:...)" >&2; \
		exit 1; \
	fi
	$(DOCKER) run --rm \
		-e MCP_HOST=$(MCP_HOST) \
		-e DATABASE_URL=$(DATABASE_URL) \
		-p $(HOST_PORT):$(CONTAINER_PORT) \
		$(IMAGE_NAME):$(IMAGE_TAG)

