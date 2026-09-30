//go:build integration

package integration

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/cookiejar"
	"net/http/httptest"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/camarokris/TDRestreamer/db"
	"github.com/camarokris/TDRestreamer/internal/httpapi"
	"github.com/camarokris/TDRestreamer/internal/store"
	"github.com/jackc/pgx/v5"
)

func TestControlBoundaries(t *testing.T) {
	ctx := context.Background()
	ownerURL, appURL := os.Getenv("TDR_TEST_OWNER_URL"), os.Getenv("TDR_TEST_APP_URL")
	if ownerURL == "" || appURL == "" {
		t.Fatal("integration requires isolated TDR_TEST_OWNER_URL and TDR_TEST_APP_URL")
	}
	owner, e := pgx.Connect(ctx, ownerURL)
	if e != nil {
		t.Fatal(e)
	}
	defer owner.Close(ctx)
	var database string
	if e = owner.QueryRow(ctx, "SELECT current_database()").Scan(&database); e != nil || !strings.HasSuffix(database, "_test") {
		t.Fatal("refusing to reset a database without _test suffix")
	}
	if _, e = owner.Exec(ctx, "DROP SCHEMA public CASCADE; CREATE SCHEMA public"); e != nil {
		t.Fatal(e)
	}
	if e = db.Migrate(ctx, ownerURL); e != nil {
		t.Fatal(e)
	}
	if e = db.Migrate(ctx, ownerURL); e != nil {
		t.Fatal("migration replay", e)
	}
	if _, e = store.Open(ctx, ownerURL); e == nil {
		t.Fatal("superuser role accepted")
	}
	st, e := store.Open(ctx, appURL)
	if e != nil {
		t.Fatal(e)
	}
	defer st.Pool.Close()
	srv := httptest.NewServer(httpapi.New(st, httpapi.Config{BootstrapToken: strings.Repeat("setup-token-", 5), RootKey: bytes.Repeat([]byte{7}, 32), MetricsToken: "test-metrics-token"}).Handler())
	defer srv.Close()
	jar, _ := cookiejar.New(nil)
	client := &http.Client{Jar: jar, Timeout: 10 * time.Second}
	call := func(client *http.Client, method, path string, body any, key string) (int, map[string]any) {
		t.Helper()
		var reader io.Reader
		if body != nil {
			b, _ := json.Marshal(body)
			reader = bytes.NewReader(b)
		}
		req, _ := http.NewRequest(method, srv.URL+path, reader)
		req.Header.Set("X-TDR-Request", "1")
		if key != "" {
			req.Header.Set("Idempotency-Key", key)
		}
		res, e := client.Do(req)
		if e != nil {
			t.Fatal(e)
		}
		defer res.Body.Close()
		raw, _ := io.ReadAll(res.Body)
		var v map[string]any
		if e = json.Unmarshal(raw, &v); e != nil {
			t.Fatalf("invalid JSON: %s", raw)
		}
		return res.StatusCode, v
	}
	anon := &http.Client{Timeout: 10 * time.Second}
	status, _ := call(anon, "GET", "/api/v1/sessions", nil, "")
	if status != 401 {
		t.Fatal("anonymous", status)
	}
	setup := map[string]any{"username": "owner", "password": "test-password-long", "tenant_name": "Alpha", "bootstrap_token": strings.Repeat("setup-token-", 5)}
	status, v := call(client, "POST", "/api/v1/auth/bootstrap", setup, "")
	if status != 201 {
		t.Fatal(status, v)
	}
	status, _ = call(client, "POST", "/api/v1/auth/bootstrap", setup, "")
	if status != 409 {
		t.Fatal("bootstrap replay", status)
	}
	status, v = call(client, "POST", "/api/v1/auth/login", map[string]string{"username": "owner", "password": "test-password-long"}, "")
	if status != 200 {
		t.Fatal(status, v)
	}
	status, me := call(client, "GET", "/api/v1/auth/me", nil, "")
	if status != 200 {
		t.Fatal(status, me)
	}
	tenant := me["tenant_id"].(string)
	status, item := call(client, "POST", "/api/v1/sessions", map[string]string{"name": "Synthetic test"}, "")
	if status != 201 {
		t.Fatal(status, item)
	}
	id := item["id"].(string)
	path := "/api/v1/sessions/" + id + "/test"
	status, item = call(client, "POST", path, map[string]int{"revision": 1}, "test-start-001")
	if status != 200 || item["state"] != "testing" {
		t.Fatal(status, item)
	}
	status, replay := call(client, "POST", path, map[string]int{"revision": 1}, "test-start-001")
	if status != 200 || replay["revision"] != item["revision"] {
		t.Fatal("idempotent replay", status, replay)
	}
	status, _ = call(client, "POST", path, map[string]int{"revision": 2}, "test-start-001")
	if status != 409 {
		t.Fatal("key reuse conflict", status)
	}
	status, _ = call(client, "POST", "/api/v1/sessions/"+id+"/go-live", map[string]int{"revision": 2}, "live-test-001")
	if status != 409 {
		t.Fatal("unqualified publishing enabled", status)
	}
	status, item = call(client, "POST", "/api/v1/sessions/"+id+"/stop", map[string]int{"revision": 2}, "stop-test-001")
	if status != 200 || item["state"] != "ended" {
		t.Fatal(status, item)
	}
	status, dest := call(client, "POST", "/api/v1/destinations", map[string]string{"name": "Sink", "platform": "generic", "url": "rtmps://example.invalid/live/extremely-sensitive-stream-key"}, "")
	if status != 201 {
		t.Fatal(status, dest)
	}
	status, v = call(client, "GET", "/api/v1/destinations", nil, "")
	raw, _ := json.Marshal(v)
	if status != 200 || bytes.Contains(raw, []byte("sensitive")) || bytes.Contains(raw, []byte("ciphertext")) {
		t.Fatal("stored secret exposed", status)
	}
	status, input := call(client, "POST", "/api/v1/inputs", map[string]string{"name": "OBS", "orientation": "horizontal"}, "")
	if status != 201 || len(input["token"].(string)) != 43 {
		t.Fatal(status, input)
	}
	status, v = call(client, "GET", "/api/v1/inputs", nil, "")
	raw, _ = json.Marshal(v)
	if bytes.Contains(raw, []byte(input["token"].(string))) {
		t.Fatal("ingest token revealed")
	}
	var tenantB string
	if e = owner.QueryRow(ctx, "INSERT INTO tenants(name) VALUES('Beta') RETURNING id::text").Scan(&tenantB); e != nil {
		t.Fatal(e)
	}
	if _, e = owner.Exec(ctx, "INSERT INTO sessions(tenant_id,name) VALUES($1::uuid,'B private session')", tenantB); e != nil {
		t.Fatal(e)
	}
	// Repeat across reused pool connections and concurrent transactions.
	var wg sync.WaitGroup
	for i := 0; i < 30; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			scope := tenant
			if i%2 == 1 {
				scope = tenantB
			}
			e := st.Tenant(ctx, scope, func(tx pgx.Tx) error {
				var count int
				if e := tx.QueryRow(ctx, "SELECT count(*) FROM sessions WHERE tenant_id::text<>$1", scope).Scan(&count); e != nil {
					return e
				}
				if count != 0 {
					return fmt.Errorf("cross-tenant rows: %d", count)
				}
				return nil
			})
			if e != nil {
				t.Error(e)
			}
		}(i)
	}
	wg.Wait()
	var count int
	if e = st.Pool.QueryRow(ctx, "SELECT count(*) FROM sessions").Scan(&count); e != nil || count != 0 {
		t.Fatal("pooled context leaked", count, e)
	}
	var secret string
	if e = owner.QueryRow(ctx, "SELECT secret::text FROM destinations WHERE id=$1::uuid", dest["id"]).Scan(&secret); e != nil || strings.Contains(secret, "sensitive") {
		t.Fatal("plaintext at rest", e)
	}
	req, _ := http.NewRequest("POST", srv.URL+"/api/v1/auth/logout", strings.NewReader("{}"))
	res, e := client.Do(req)
	if e != nil {
		t.Fatal(e)
	}
	res.Body.Close()
	if res.StatusCode != 403 {
		t.Fatal("CSRF bypass")
	}
	// Viewer membership takes effect immediately on an existing session.
	if _, e = owner.Exec(ctx, "UPDATE memberships SET role='viewer' WHERE user_id=$1::uuid", me["user_id"]); e != nil {
		t.Fatal(e)
	}
	status, _ = call(client, "POST", "/api/v1/sessions", map[string]string{"name": "not allowed"}, "")
	if status != 403 {
		t.Fatal("viewer mutation", status)
	}
	status, _ = call(client, "POST", "/api/v1/auth/logout", map[string]string{}, "")
	if status != 200 {
		t.Fatal(status)
	}
	status, _ = call(client, "GET", "/api/v1/auth/me", nil, "")
	if status != 401 {
		t.Fatal("logout not revoked")
	}
	// Leave the disposable fixture usable by the separate browser acceptance suite.
	if _, e = owner.Exec(ctx, "UPDATE memberships SET role='admin' WHERE user_id=$1::uuid", me["user_id"]); e != nil {
		t.Fatal(e)
	}

}
