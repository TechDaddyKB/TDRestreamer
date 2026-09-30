// Package db embeds versioned migrations for the administrator command.
package db

import (
	"context"
	"embed"
	"fmt"
	"github.com/jackc/pgx/v5"
	"sort"
	"strconv"
	"strings"
)

//go:embed migrations/*.sql
var migrations embed.FS

func Migrate(ctx context.Context, url string) error {
	conn, e := pgx.Connect(ctx, url)
	if e != nil {
		return fmt.Errorf("migration database connection failed")
	}
	defer conn.Close(ctx)
	tx, e := conn.Begin(ctx)
	if e != nil {
		return e
	}
	defer tx.Rollback(ctx)
	if _, e = tx.Exec(ctx, "SELECT pg_advisory_xact_lock(843741)"); e != nil {
		return e
	}
	var exists bool
	if e = tx.QueryRow(ctx, "SELECT to_regclass('public.schema_versions') IS NOT NULL").Scan(&exists); e != nil {
		return e
	}
	current := 0
	if exists {
		if e = tx.QueryRow(ctx, "SELECT coalesce(max(version),0) FROM schema_versions").Scan(&current); e != nil {
			return e
		}
	}
	files, e := migrations.ReadDir("migrations")
	if e != nil {
		return e
	}
	sort.Slice(files, func(i, j int) bool { return files[i].Name() < files[j].Name() })
	for _, f := range files {
		v, e := strconv.Atoi(strings.Split(f.Name(), "_")[0])
		if e != nil {
			return e
		}
		if v <= current {
			continue
		}
		sql, e := migrations.ReadFile("migrations/" + f.Name())
		if e != nil {
			return e
		}
		if _, e = tx.Exec(ctx, string(sql)); e != nil {
			return fmt.Errorf("migration %s: %w", f.Name(), e)
		}
	}
	return tx.Commit(ctx)
}
