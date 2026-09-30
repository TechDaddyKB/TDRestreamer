package httpapi

import (
	"context"
	"crypto/subtle"
	"encoding/json"
	"errors"
	"github.com/camarokris/TDRestreamer/internal/auth"
	"github.com/camarokris/TDRestreamer/internal/secrets"
	"github.com/camarokris/TDRestreamer/internal/store"
	"github.com/jackc/pgx/v5"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

type Config struct {
	BootstrapToken string
	RootKey        []byte
	SecureCookies  bool
	Cloud          bool
	WebDir         string
	MetricsToken   string
}
type Server struct {
	Store         *store.Store
	Config        Config
	requests      atomic.Uint64
	mu            sync.Mutex
	attempts      map[string]attempt
	passwordSlots chan struct{}
}
type attempt struct {
	count int
	since time.Time
}
type principalKey struct{}

func New(s *store.Store, c Config) *Server {
	return &Server{Store: s, Config: c, attempts: map[string]attempt{}, passwordSlots: make(chan struct{}, 4)}
}
func (s *Server) Handler() http.Handler {
	m := http.NewServeMux()
	m.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) { write(w, 200, map[string]string{"status": "ok"}) })
	m.HandleFunc("GET /readyz", func(w http.ResponseWriter, r *http.Request) {
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()
		if s.Store.Pool.Ping(ctx) != nil {
			fail(w, 503, "not_ready", "Database unavailable")
			return
		}
		write(w, 200, map[string]string{"status": "ready"})
	})
	m.HandleFunc("GET /metrics", s.metrics)
	m.HandleFunc("POST /api/v1/auth/bootstrap", s.bootstrap)
	m.HandleFunc("POST /api/v1/auth/login", s.login)
	m.Handle("POST /api/v1/auth/logout", s.protect("view", http.HandlerFunc(s.logout)))
	m.Handle("GET /api/v1/auth/me", s.protect("view", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { write(w, 200, principal(r)) })))
	m.Handle("GET /api/v1/sessions", s.protect("view", http.HandlerFunc(s.listSessions)))
	m.Handle("POST /api/v1/sessions", s.protect("operate", http.HandlerFunc(s.createSession)))
	m.Handle("POST /api/v1/sessions/{id}/{action}", s.protect("operate", http.HandlerFunc(s.sessionAction)))
	m.Handle("GET /api/v1/inputs", s.protect("view", http.HandlerFunc(s.listInputs)))
	m.Handle("POST /api/v1/inputs", s.protect("edit", http.HandlerFunc(s.createInput)))
	m.Handle("POST /api/v1/inputs/{id}/rotate", s.protect("secrets", http.HandlerFunc(s.rotateInput)))
	m.Handle("GET /api/v1/destinations", s.protect("view", http.HandlerFunc(s.listDestinations)))
	m.Handle("POST /api/v1/destinations", s.protect("secrets", http.HandlerFunc(s.createDestination)))
	m.Handle("POST /api/v1/compatibility/evaluate", s.protect("view", http.HandlerFunc(s.evaluate)))
	m.Handle("GET /api/v1/capabilities", s.protect("view", http.HandlerFunc(s.capabilities)))
	m.Handle("GET /api/v1/events", s.protect("view", http.HandlerFunc(s.events)))
	m.HandleFunc("GET /api/v1/openapi.json", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(openAPI)
	})
	m.HandleFunc("GET /api/", func(w http.ResponseWriter, r *http.Request) { fail(w, 404, "not_found", "API route not found") })
	m.HandleFunc("GET /", s.static)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		s.requests.Add(1)
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Referrer-Policy", "no-referrer")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("Content-Security-Policy", "default-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
		if strings.HasPrefix(r.URL.Path, "/api/") {
			w.Header().Set("Cache-Control", "no-store")
		}
		// Browser cross-origin forms cannot set this header; no CORS is enabled.
		if r.Method != "GET" && r.Method != "HEAD" && r.Method != "OPTIONS" && r.Header.Get("X-TDR-Request") != "1" {
			fail(w, 403, "csrf", "Missing same-origin request header")
			return
		}
		m.ServeHTTP(w, r)
	})
}
func (s *Server) static(w http.ResponseWriter, r *http.Request) {
	if strings.HasPrefix(r.URL.Path, "/api/") {
		fail(w, 404, "not_found", "API route not found")
		return
	}
	clean := filepath.Clean("/" + r.URL.Path)
	path := filepath.Join(s.Config.WebDir, clean)
	if info, e := os.Stat(path); e == nil && !info.IsDir() {
		http.ServeFile(w, r, path)
		return
	}
	http.ServeFile(w, r, filepath.Join(s.Config.WebDir, "index.html"))
}
func write(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
func fail(w http.ResponseWriter, status int, code, message string) {
	write(w, status, map[string]any{"error": map[string]string{"code": code, "message": message}})
}
func decode(w http.ResponseWriter, r *http.Request, v any) bool {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	d := json.NewDecoder(r.Body)
	d.DisallowUnknownFields()
	if err := d.Decode(v); err != nil {
		fail(w, 400, "invalid_json", "Request must match the documented JSON schema")
		return false
	}
	if d.Decode(&struct{}{}) != io.EOF {
		fail(w, 400, "invalid_json", "Only one JSON value is accepted")
		return false
	}
	return true
}
func principal(r *http.Request) auth.Principal {
	return r.Context().Value(principalKey{}).(auth.Principal)
}
func sessionToken(r *http.Request) string {
	if strings.HasPrefix(r.Header.Get("Authorization"), "Bearer ") {
		return strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer ")
	}
	c, e := r.Cookie("tdr_session")
	if e != nil {
		return ""
	}
	return c.Value
}
func (s *Server) protect(action string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		token := sessionToken(r)
		if len(token) != 43 {
			fail(w, 401, "unauthorized", "Sign in to continue")
			return
		}
		var p auth.Principal
		e := s.Store.Pool.QueryRow(r.Context(), `SELECT a.user_id::text,a.tenant_id::text,m.role,m.edit_granted FROM auth_sessions a JOIN memberships m ON m.user_id=a.user_id AND m.tenant_id=a.tenant_id WHERE a.token_hash=$1 AND a.expires_at>now()`, secrets.Hash(token)).Scan(&p.UserID, &p.TenantID, &p.Role, &p.EditGranted)
		if errors.Is(e, pgx.ErrNoRows) {
			fail(w, 401, "unauthorized", "Session expired or revoked")
			return
		}
		if e != nil {
			fail(w, 503, "database_unavailable", "Authentication temporarily unavailable")
			return
		}
		if !p.Allows(p.TenantID, action) {
			fail(w, 403, "forbidden", "Your role does not allow this action")
			return
		}
		next.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), principalKey{}, p)))
	})
}
func (s *Server) allowLogin(r *http.Request) bool {
	host, _, e := net.SplitHostPort(r.RemoteAddr)
	if e != nil {
		host = r.RemoteAddr
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	now := time.Now()
	for key, a := range s.attempts {
		if now.Sub(a.since) > time.Minute {
			delete(s.attempts, key)
		}
	}
	a := s.attempts[host]
	if a.since.IsZero() {
		if len(s.attempts) >= 4096 {
			return false
		}
		a.since = now
	}
	a.count++
	s.attempts[host] = a
	return a.count <= 10
}
func (s *Server) metrics(w http.ResponseWriter, r *http.Request) {
	token := strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer ")
	if s.Config.MetricsToken == "" || subtle.ConstantTimeCompare([]byte(token), []byte(s.Config.MetricsToken)) != 1 {
		fail(w, 401, "unauthorized", "Metrics token required")
		return
	}
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	io.WriteString(w, "# HELP tdr_http_requests_total HTTP requests received.\n# TYPE tdr_http_requests_total counter\ntdr_http_requests_total "+strconv.FormatUint(s.requests.Load(), 10)+"\n")
}
func dbFailure(w http.ResponseWriter, err error) {
	if errors.Is(err, pgx.ErrNoRows) {
		fail(w, 404, "not_found", "Resource not found")
	} else {
		fail(w, 500, "operation_failed", "Operation failed; no secret details are exposed")
	}
}
func validName(s string) bool { return len(strings.TrimSpace(s)) > 0 && len(s) <= 120 }
func validID(s string) bool {
	if len(s) != 36 {
		return false
	}
	for i, c := range s {
		if i == 8 || i == 13 || i == 18 || i == 23 {
			if c != '-' {
				return false
			}
		} else if !strings.ContainsRune("0123456789abcdefABCDEF", c) {
			return false
		}
	}
	return true
}
