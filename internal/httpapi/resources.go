package httpapi

import (
	"encoding/json"
	"github.com/camarokris/TDRestreamer/internal/planner"
	"github.com/camarokris/TDRestreamer/internal/secrets"
	"github.com/jackc/pgx/v5"
	"net/http"
	"net/url"
	"strings"
)

func audit(r *http.Request, tx pgx.Tx, action, id string) error {
	p := principal(r)
	_, e := tx.Exec(r.Context(), "INSERT INTO audit_events(tenant_id,actor_id,action,resource_id) VALUES($1::uuid,$2::uuid,$3,$4)", p.TenantID, p.UserID, action, id)
	return e
}
func (s *Server) listInputs(w http.ResponseWriter, r *http.Request) {
	result := []map[string]any{}
	e := s.Store.Tenant(r.Context(), principal(r).TenantID, func(tx pgx.Tx) error {
		rows, e := tx.Query(r.Context(), "SELECT id::text,name,orientation FROM inputs ORDER BY created_at LIMIT 100")
		if e != nil {
			return e
		}
		defer rows.Close()
		for rows.Next() {
			var id, name, orientation string
			if e = rows.Scan(&id, &name, &orientation); e != nil {
				return e
			}
			result = append(result, map[string]any{"id": id, "name": name, "orientation": orientation, "credential_set": true})
		}
		return rows.Err()
	})
	if e != nil {
		dbFailure(w, e)
		return
	}
	write(w, 200, map[string]any{"items": result})
}
func (s *Server) createInput(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Name        string `json:"name"`
		Orientation string `json:"orientation"`
	}
	if !decode(w, r, &body) {
		return
	}
	if !validName(body.Name) || (body.Orientation != "horizontal" && body.Orientation != "vertical" && body.Orientation != "master") {
		fail(w, 400, "invalid_input", "Name and input orientation are required")
		return
	}
	token, e := secrets.Token()
	if e != nil {
		dbFailure(w, e)
		return
	}
	var id string
	e = s.Store.Tenant(r.Context(), principal(r).TenantID, func(tx pgx.Tx) error {
		if e := tx.QueryRow(r.Context(), "INSERT INTO inputs(tenant_id,name,orientation,token_hash) VALUES($1::uuid,$2,$3,$4) RETURNING id::text", principal(r).TenantID, body.Name, body.Orientation, secrets.Hash(token)).Scan(&id); e != nil {
			return e
		}
		return audit(r, tx, "input.create", id)
	})
	if e != nil {
		dbFailure(w, e)
		return
	}
	write(w, 201, map[string]string{"id": id, "token": token, "path": "inputs/" + id, "status": "configuration_only"})
}
func (s *Server) rotateInput(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if !validID(id) {
		fail(w, 400, "invalid_id", "Invalid input ID")
		return
	}
	token, e := secrets.Token()
	if e != nil {
		dbFailure(w, e)
		return
	}
	e = s.Store.Tenant(r.Context(), principal(r).TenantID, func(tx pgx.Tx) error {
		tag, e := tx.Exec(r.Context(), "UPDATE inputs SET token_hash=$1 WHERE id=$2::uuid", secrets.Hash(token), id)
		if e != nil {
			return e
		}
		if tag.RowsAffected() != 1 {
			return pgx.ErrNoRows
		}
		return audit(r, tx, "input.rotate", id)
	})
	if e != nil {
		dbFailure(w, e)
		return
	}
	write(w, 200, map[string]string{"token": token})
}
func (s *Server) listDestinations(w http.ResponseWriter, r *http.Request) {
	result := []map[string]any{}
	e := s.Store.Tenant(r.Context(), principal(r).TenantID, func(tx pgx.Tx) error {
		rows, e := tx.Query(r.Context(), "SELECT id::text,name,platform FROM destinations ORDER BY created_at LIMIT 100")
		if e != nil {
			return e
		}
		defer rows.Close()
		for rows.Next() {
			var id, name, platform string
			if e = rows.Scan(&id, &name, &platform); e != nil {
				return e
			}
			result = append(result, map[string]any{"id": id, "name": name, "platform": platform, "credential_set": true})
		}
		return rows.Err()
	})
	if e != nil {
		dbFailure(w, e)
		return
	}
	write(w, 200, map[string]any{"items": result})
}
func (s *Server) createDestination(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Name     string `json:"name"`
		Platform string `json:"platform"`
		URL      string `json:"url"`
	}
	if !decode(w, r, &body) {
		return
	}
	u, e := url.Parse(body.URL)
	if e != nil || u.Hostname() == "" || (u.Scheme != "rtmp" && u.Scheme != "rtmps") || u.User != nil || !validName(body.Name) || len(body.URL) > 4096 || !strings.Contains("|generic|youtube|twitch|kick|x|rumble|", "|"+body.Platform+"|") || body.Platform == "" {
		fail(w, 400, "invalid_destination", "Provide a name, supported platform and RTMP/RTMPS URL without userinfo")
		return
	}
	// This stores configuration only. DNS/pinned dialing must be validated at execution.
	var id string
	e = s.Store.Tenant(r.Context(), principal(r).TenantID, func(tx pgx.Tx) error {
		if e := tx.QueryRow(r.Context(), "SELECT gen_random_uuid()::text").Scan(&id); e != nil {
			return e
		}
		envelope, e := secrets.Encrypt("v1", s.Config.RootKey, []byte(body.URL), principal(r).TenantID+"/"+id)
		if e != nil {
			return e
		}
		raw, e := json.Marshal(envelope)
		if e != nil {
			return e
		}
		if _, e = tx.Exec(r.Context(), "INSERT INTO destinations(id,tenant_id,name,platform,secret) VALUES($1::uuid,$2::uuid,$3,$4,$5)", id, principal(r).TenantID, body.Name, body.Platform, raw); e != nil {
			return e
		}
		return audit(r, tx, "destination.create", id)
	})
	if e != nil {
		dbFailure(w, e)
		return
	}
	write(w, 201, map[string]any{"id": id, "credential_set": true})
}
func (s *Server) evaluate(w http.ResponseWriter, r *http.Request) {
	var req planner.Request
	if !decode(w, r, &req) {
		return
	}
	if req.RuleRevision != "generic-v1" {
		fail(w, 400, "unknown_rules", "Only generic-v1 is implemented; platform acceptance is not implied")
		return
	}
	p, e := planner.Evaluate(req)
	if e != nil {
		fail(w, 400, "invalid_profile", e.Error())
		return
	}
	write(w, 200, p)
}
func (s *Server) capabilities(w http.ResponseWriter, r *http.Request) {
	write(w, 200, map[string]any{"release": "development", "publishing": false, "preview": false, "remote_workers": false, "cloud_provisioning": false, "authentication": []string{"local"}, "platform_qualification": "blocked: local tests only", "planner": "generic-v1; codec/geometry proposal only"})
}
