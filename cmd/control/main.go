package main

import (
	"context"
	"encoding/base64"
	"github.com/camarokris/TDRestreamer/internal/httpapi"
	"github.com/camarokris/TDRestreamer/internal/store"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	if err := run(); err != nil {
		slog.Error("control stopped", "reason", err.Error())
		os.Exit(1)
	}
}
func run() error {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()
	root, e := base64.StdEncoding.DecodeString(os.Getenv("TDR_ROOT_KEY"))
	if e != nil || len(root) != 32 {
		return configError("TDR_ROOT_KEY must be a base64 32-byte key")
	}
	url := os.Getenv("DATABASE_URL")
	if url == "" {
		return configError("DATABASE_URL is required")
	}
	startCtx, stop := context.WithTimeout(ctx, 10*time.Second)
	defer stop()
	st, e := store.Open(startCtx, url)
	if e != nil {
		return e
	}
	defer st.Pool.Close()
	addr := os.Getenv("TDR_LISTEN")
	if addr == "" {
		addr = "127.0.0.1:8080"
	}
	web := os.Getenv("TDR_WEB_DIR")
	if web == "" {
		web = "web/dist"
	}
	cloud := os.Getenv("TDR_MODE") == "cloud"
	if cloud {
		return configError("cloud deployment is not enabled until OAuth/recovery and TLS preflight are implemented")
	}
	api := httpapi.New(st, httpapi.Config{BootstrapToken: os.Getenv("TDR_BOOTSTRAP_TOKEN"), RootKey: root, MetricsToken: os.Getenv("TDR_METRICS_TOKEN"), WebDir: web, SecureCookies: os.Getenv("TDR_SECURE_COOKIES") == "true", Cloud: cloud})
	server := &http.Server{Addr: addr, Handler: api.Handler(), ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, IdleTimeout: 60 * time.Second, MaxHeaderBytes: 32768, BaseContext: func(net.Listener) context.Context { return ctx }}
	go func() {
		<-ctx.Done()
		stopCtx, done := context.WithTimeout(context.Background(), 5*time.Second)
		defer done()
		server.Shutdown(stopCtx)
	}()
	slog.Info("Tech Daddy's Restreamer control started", "listen", addr, "release", "development")
	e = server.ListenAndServe()
	if e == http.ErrServerClosed {
		return nil
	}
	return e
}

type configError string

func (e configError) Error() string { return string(e) }
