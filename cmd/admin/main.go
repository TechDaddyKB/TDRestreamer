package main

import (
	"context"
	"encoding/base64"
	"fmt"
	"github.com/camarokris/TDRestreamer/db"
	"github.com/camarokris/TDRestreamer/internal/secrets"
	"net/http"
	"os"
	"time"
)

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: admin migrate | token | root-key | health")
		os.Exit(2)
	}
	switch os.Args[1] {
	case "health":
		client := http.Client{Timeout: 2 * time.Second}
		res, err := client.Get("http://127.0.0.1:8080/readyz")
		if err != nil {
			os.Exit(1)
		}
		res.Body.Close()
		if res.StatusCode != 200 {
			os.Exit(1)
		}
	case "migrate":
		if err := db.Migrate(context.Background(), os.Getenv("TDR_MIGRATION_DATABASE_URL")); err != nil {
			fmt.Fprintln(os.Stderr, "migration failed:", err)
			os.Exit(1)
		}
	case "token":
		v, e := secrets.Token()
		if e != nil {
			os.Exit(1)
		}
		fmt.Println(v)
	case "root-key":
		v, e := secrets.Token()
		if e != nil {
			os.Exit(1)
		}
		b, e := base64.RawURLEncoding.DecodeString(v)
		if e != nil {
			os.Exit(1)
		}
		fmt.Println(base64.StdEncoding.EncodeToString(b))
	default:
		fmt.Fprintln(os.Stderr, "unknown command")
		os.Exit(2)
	}
}
