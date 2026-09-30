GO ?= go
.PHONY: setup check fmt lint unit integration browser media m0 docs build image generate
setup:
	cd web && npm ci --ignore-scripts
fmt:
	$(GO) fmt ./...
lint:
	$(GO) vet ./...
	cd web && npm run typecheck
	cd web && npm run format:check
unit:
	python3 -m unittest discover -s tests/m0 -p 'test_*.py'
	$(GO) test -race -cover ./...
	cd web && npm test
integration:
	$(GO) test -race -tags=integration ./tests/integration/... -count=1
browser:
	cd web && npm run test:e2e
media:
	$(GO) test -tags=media ./tests/media/...
	python3 scripts/media-spike.py
m0:
	python3 scripts/m0-local.py
build:
	mkdir -p bin
	$(GO) build -trimpath -o bin/control ./cmd/control
	$(GO) build -trimpath -o bin/admin ./cmd/admin
	$(GO) build -trimpath -o bin/worker ./cmd/worker
	cd web && npm run build
image:
	docker build -t tdrestreamer:development .
generate:
	$(GO) run github.com/sqlc-dev/sqlc/cmd/sqlc@v1.31.1 generate
	cd web && npm run api:generate
docs:
	python3 scripts/check-docs.py
check: lint unit docs build
