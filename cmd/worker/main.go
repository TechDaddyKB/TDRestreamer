// The worker entrypoint is diagnostic-only until the M0 media gate is closed.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strings"
)

func main() {
	if len(os.Args) != 2 || os.Args[1] != "probe" {
		fmt.Fprintln(os.Stderr, "usage: worker probe; job execution is not yet implemented")
		os.Exit(2)
	}
	out, e := exec.Command("ffmpeg", "-version").Output()
	version := "unavailable"
	if e == nil {
		version = strings.SplitN(string(out), "\n", 2)[0]
	}
	json.NewEncoder(os.Stdout).Encode(map[string]any{"architecture": runtime.GOARCH, "os": runtime.GOOS, "ffmpeg": version, "encoder_capacity_verified": false, "accepts_jobs": false})
}
