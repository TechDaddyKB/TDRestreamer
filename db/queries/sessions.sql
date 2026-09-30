-- name: ListSessions :many
SELECT id::text, tenant_id::text, name, state, mode, revision, created_at, updated_at FROM sessions WHERE tenant_id = $1::uuid ORDER BY created_at DESC LIMIT $2 OFFSET $3;

-- name: GetSession :one
SELECT id::text, tenant_id::text, name, state, mode, revision, created_at, updated_at FROM sessions WHERE tenant_id = $1::uuid AND id = $2::uuid FOR UPDATE;

-- name: CreateSession :one
INSERT INTO sessions(tenant_id,name) VALUES($1::uuid,$2) RETURNING id::text, tenant_id::text, name, state, mode, revision, created_at, updated_at;

-- name: UpdateSession :one
UPDATE sessions SET state=$3, mode=$4, revision=revision+1,updated_at=now() WHERE tenant_id=$1::uuid AND id=$2::uuid AND revision=$5 RETURNING id::text, tenant_id::text, name, state, mode, revision, created_at, updated_at;
