package httpapi

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/camarokris/TDRestreamer/internal/dbgen"
	"github.com/camarokris/TDRestreamer/internal/secrets"
	"github.com/camarokris/TDRestreamer/internal/sessions"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"net/http"
	"strconv"
	"strings"
	"time"
)

func uuid(s string) pgtype.UUID { var id pgtype.UUID; _ = id.Scan(s); return id }
func (s *Server) listSessions(w http.ResponseWriter, r *http.Request) {
	offset, _ := strconv.Atoi(r.URL.Query().Get("offset"))
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	if limit <= 0 || limit > 100 {
		limit = 50
	}
	if offset < 0 || offset > 1000000 {
		offset = 0
	}
	var items []dbgen.ListSessionsRow
	e := s.Store.Tenant(r.Context(), principal(r).TenantID, func(tx pgx.Tx) error {
		var e error
		items, e = dbgen.New(tx).ListSessions(r.Context(), dbgen.ListSessionsParams{Column1: uuid(principal(r).TenantID), Limit: int32(limit), Offset: int32(offset)})
		return e
	})
	if e != nil {
		dbFailure(w, e)
		return
	}
	write(w, 200, map[string]any{"items": items, "offset": offset, "limit": limit})
}
func (s *Server) createSession(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Name string `json:"name"`
	}
	if !decode(w, r, &body) {
		return
	}
	if !validName(body.Name) {
		fail(w, 400, "invalid_name", "Session name is required (maximum 120 bytes)")
		return
	}
	var item dbgen.CreateSessionRow
	e := s.Store.Tenant(r.Context(), principal(r).TenantID, func(tx pgx.Tx) error {
		var e error
		item, e = dbgen.New(tx).CreateSession(r.Context(), dbgen.CreateSessionParams{Column1: uuid(principal(r).TenantID), Name: body.Name})
		if e != nil {
			return e
		}
		return audit(r, tx, "session.create", item.ID)
	})
	if e != nil {
		dbFailure(w, e)
		return
	}
	write(w, 201, item)
}

var errConflict = errors.New("revision or idempotency conflict")

func (s *Server) sessionAction(w http.ResponseWriter, r *http.Request) {
	id, action := r.PathValue("id"), r.PathValue("action")
	if !validID(id) {
		fail(w, 400, "invalid_id", "Invalid session ID")
		return
	}
	if action == "go-live" {
		fail(w, 409, "qualification_required", "Publishing is disabled until the media execution path is implemented and qualified")
		return
	}
	if action != "test" && action != "prepare" && action != "stop" {
		fail(w, 404, "not_found", "Unknown session action")
		return
	}
	var body struct {
		Revision int64 `json:"revision"`
	}
	if !decode(w, r, &body) {
		return
	}
	key := r.Header.Get("Idempotency-Key")
	if len(key) < 8 || len(key) > 128 {
		fail(w, 400, "idempotency_required", "Supply an Idempotency-Key of 8 to 128 bytes")
		return
	}
	hash := secrets.Hash(principal(r).UserID + ":" + id + ":" + action + ":" + strconv.FormatInt(body.Revision, 10))
	var response json.RawMessage
	e := s.Store.Tenant(r.Context(), principal(r).TenantID, func(tx pgx.Tx) error {
		// Serialize reuse of a key even when requests target different resources.
		if _, e := tx.Exec(r.Context(), "SELECT pg_advisory_xact_lock(hashtextextended($1,0))", principal(r).TenantID+":"+key); e != nil {
			return e
		}
		var existing []byte
		e := tx.QueryRow(r.Context(), "SELECT request_hash,response FROM idempotency WHERE key=$1", key).Scan(&existing, &response)
		if e == nil {
			if !bytes.Equal(existing, hash) {
				return errConflict
			}
			return nil
		}
		if !errors.Is(e, pgx.ErrNoRows) {
			return e
		}
		q := dbgen.New(tx)
		item, e := q.GetSession(r.Context(), dbgen.GetSessionParams{Column1: uuid(principal(r).TenantID), Column2: uuid(id)})
		if e != nil {
			return e
		}
		if item.Revision != body.Revision {
			return errConflict
		}
		next, e := sessions.Transition(sessions.State(item.State), action)
		if e != nil {
			return e
		}
		if action == "stop" {
			next = sessions.Ended
		} // No executor exists yet, so there are no processes to drain.
		updated, e := q.UpdateSession(r.Context(), dbgen.UpdateSessionParams{Column1: uuid(principal(r).TenantID), Column2: uuid(id), State: string(next), Mode: "test", Revision: item.Revision})
		if e != nil {
			return e
		}
		response, e = json.Marshal(updated)
		if e != nil {
			return e
		}
		if _, e = tx.Exec(r.Context(), "INSERT INTO idempotency(tenant_id,key,request_hash,response) VALUES($1::uuid,$2,$3,$4)", principal(r).TenantID, key, hash, []byte(response)); e != nil {
			return e
		}
		if _, e = tx.Exec(r.Context(), "INSERT INTO outbox(tenant_id,resource_id,kind,payload) VALUES($1::uuid,$2::uuid,$3,$4)", principal(r).TenantID, id, "session."+action, []byte(response)); e != nil {
			return e
		}
		return audit(r, tx, "session."+action, id)
	})
	if errors.Is(e, errConflict) || errors.Is(e, sessions.ErrTransition) {
		fail(w, 409, "state_conflict", "Refresh the session revision or use a new idempotency key for a different action")
		return
	}
	if e != nil {
		dbFailure(w, e)
		return
	}
	write(w, 200, response)
}
func (s *Server) events(w http.ResponseWriter, r *http.Request) {
	f, ok := w.(http.Flusher)
	if !ok {
		fail(w, 500, "stream_unavailable", "Event streaming unavailable")
		return
	}
	cursor, _ := strconv.ParseInt(r.Header.Get("Last-Event-ID"), 10, 64)
	if cursor < 0 {
		cursor = 0
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("X-Accel-Buffering", "no")
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()
	deadline := time.NewTimer(time.Minute)
	defer deadline.Stop() // Re-authenticate on reconnect; bound revoked session lifetime.
	for {
		var events []struct {
			ID      int64
			Kind    string
			Payload []byte
		}
		e := s.Store.Tenant(r.Context(), principal(r).TenantID, func(tx pgx.Tx) error {
			rows, e := tx.Query(r.Context(), "SELECT id,kind,payload FROM outbox WHERE id>$1 ORDER BY id LIMIT 100", cursor)
			if e != nil {
				return e
			}
			defer rows.Close()
			for rows.Next() {
				var event struct {
					ID      int64
					Kind    string
					Payload []byte
				}
				if e = rows.Scan(&event.ID, &event.Kind, &event.Payload); e != nil {
					return e
				}
				events = append(events, event)
			}
			return rows.Err()
		})
		if e != nil {
			return
		}
		_ = http.NewResponseController(w).SetWriteDeadline(time.Now().Add(10 * time.Second))
		for _, event := range events {
			fmt.Fprintf(w, "id: %d\nevent: %s\ndata: %s\n\n", event.ID, strings.ReplaceAll(event.Kind, "\n", ""), event.Payload)
			cursor = event.ID
		}
		fmt.Fprint(w, ": heartbeat\n\n")
		f.Flush()
		select {
		case <-r.Context().Done():
			return
		case <-deadline.C:
			return
		case <-ticker.C:
		}
	}
}
