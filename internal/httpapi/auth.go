package httpapi

import (
	"crypto/subtle"
	"errors"
	"github.com/camarokris/TDRestreamer/internal/auth"
	"github.com/camarokris/TDRestreamer/internal/secrets"
	"github.com/jackc/pgx/v5"
	"net/http"
	"strings"
	"time"
)

type credentials struct {
	Username       string `json:"username"`
	Password       string `json:"password"`
	BootstrapToken string `json:"bootstrap_token,omitempty"`
	TenantName     string `json:"tenant_name,omitempty"`
}

func (s *Server) bootstrap(w http.ResponseWriter, r *http.Request) {
	if !s.allowLogin(r) {
		fail(w, 429, "rate_limited", "Try again in one minute")
		return
	}
	var c credentials
	if !decode(w, r, &c) {
		return
	}
	if len(s.Config.BootstrapToken) < 32 || subtle.ConstantTimeCompare([]byte(c.BootstrapToken), []byte(s.Config.BootstrapToken)) != 1 {
		fail(w, 403, "bootstrap_denied", "Invalid setup credential")
		return
	}
	if !validName(c.Username) || strings.ContainsAny(c.Username, " \t\n") || !validName(c.TenantName) {
		fail(w, 400, "invalid_identity", "Choose a username and workspace name")
		return
	}
	select {
	case s.passwordSlots <- struct{}{}:
		defer func() { <-s.passwordSlots }()
	default:
		fail(w, 429, "rate_limited", "Authentication busy")
		return
	}
	hash, e := auth.PasswordHash(c.Password)
	if e != nil {
		fail(w, 400, "invalid_password", e.Error())
		return
	}
	tx, e := s.Store.Pool.Begin(r.Context())
	if e != nil {
		dbFailure(w, e)
		return
	}
	defer tx.Rollback(r.Context())
	_, e = tx.Exec(r.Context(), "SELECT pg_advisory_xact_lock(843742)")
	if e != nil {
		dbFailure(w, e)
		return
	}
	var count int
	if e = tx.QueryRow(r.Context(), "SELECT count(*) FROM users").Scan(&count); e != nil {
		dbFailure(w, e)
		return
	}
	if count != 0 {
		fail(w, 409, "already_configured", "Initial setup has already been completed")
		return
	}
	var user, tenant string
	if e = tx.QueryRow(r.Context(), "INSERT INTO users(username,password_hash) VALUES($1,$2) RETURNING id::text", c.Username, hash).Scan(&user); e != nil {
		dbFailure(w, e)
		return
	}
	if e = tx.QueryRow(r.Context(), "INSERT INTO tenants(name) VALUES($1) RETURNING id::text", c.TenantName).Scan(&tenant); e != nil {
		dbFailure(w, e)
		return
	}
	if _, e = tx.Exec(r.Context(), "INSERT INTO memberships(user_id,tenant_id,role) VALUES($1::uuid,$2::uuid,'admin')", user, tenant); e != nil {
		dbFailure(w, e)
		return
	}
	if e = tx.Commit(r.Context()); e != nil {
		dbFailure(w, e)
		return
	}
	write(w, 201, map[string]string{"status": "configured", "next": "Sign in with your new local account"})
}
func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	if s.Config.Cloud {
		fail(w, 403, "recovery_only", "Cloud local login is recovery-only; use the host administrator workflow")
		return
	}
	if !s.allowLogin(r) {
		fail(w, 429, "rate_limited", "Try again in one minute")
		return
	}
	var c credentials
	if !decode(w, r, &c) {
		return
	}
	select {
	case s.passwordSlots <- struct{}{}:
		defer func() { <-s.passwordSlots }()
	default:
		fail(w, 429, "rate_limited", "Authentication busy")
		return
	}
	var user, hash, tenant string
	e := s.Store.Pool.QueryRow(r.Context(), "SELECT u.id::text,u.password_hash,m.tenant_id::text FROM users u JOIN memberships m ON m.user_id=u.id WHERE username=$1 ORDER BY m.tenant_id LIMIT 1", c.Username).Scan(&user, &hash, &tenant)
	if e != nil && !errors.Is(e, pgx.ErrNoRows) {
		dbFailure(w, e)
		return
	}
	if e != nil {
		hash = "argon2id-v1$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
	}
	if !auth.PasswordMatches(hash, c.Password) || user == "" {
		fail(w, 401, "invalid_credentials", "Username or password is incorrect")
		return
	}
	token, e := secrets.Token()
	if e != nil {
		dbFailure(w, e)
		return
	}
	_, e = s.Store.Pool.Exec(r.Context(), "INSERT INTO auth_sessions(token_hash,user_id,tenant_id,expires_at) VALUES($1,$2::uuid,$3::uuid,$4)", secrets.Hash(token), user, tenant, time.Now().Add(12*time.Hour))
	if e != nil {
		dbFailure(w, e)
		return
	}
	http.SetCookie(w, &http.Cookie{Name: "tdr_session", Value: token, Path: "/", HttpOnly: true, Secure: s.Config.SecureCookies, SameSite: http.SameSiteStrictMode, MaxAge: 43200})
	write(w, 200, map[string]string{"status": "signed_in"})
}
func (s *Server) logout(w http.ResponseWriter, r *http.Request) {
	if _, e := s.Store.Pool.Exec(r.Context(), "DELETE FROM auth_sessions WHERE token_hash=$1", secrets.Hash(sessionToken(r))); e != nil {
		dbFailure(w, e)
		return
	}
	http.SetCookie(w, &http.Cookie{Name: "tdr_session", Value: "", Path: "/", HttpOnly: true, Secure: s.Config.SecureCookies, SameSite: http.SameSiteStrictMode, MaxAge: -1})
	write(w, 200, map[string]string{"status": "signed_out"})
}
