//go:build media

package media

import (
	"bytes"
	"context"
	"os/exec"
	"testing"
	"time"

	"github.com/camarokris/TDRestreamer/internal/planner"
)

func render(t *testing.T, source, filter string, width, height int) []byte {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", source, "-vf", filter, "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1")
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	pixels, err := cmd.Output()
	if err != nil {
		t.Fatalf("render failed: %v: %s", err, stderr.String())
	}
	if len(pixels) != width*height*3 {
		t.Fatalf("wrong rendered dimensions: %d bytes", len(pixels))
	}
	return pixels
}

func TestVerticalModesRenderRealFrames(t *testing.T) {
	for _, mode := range []string{"crop", "fill", "blur"} {
		t.Run(mode, func(t *testing.T) {
			filter, err := planner.VerticalFilter(mode, 640, 360, 180, 320, 0.5)
			if err != nil {
				t.Fatal(err)
			}
			pixels := render(t, "color=c=red:s=640x360:r=30", filter, 180, 320)
			center := (160*180 + 90) * 3
			if pixels[center] < 200 || pixels[center+2] > 50 {
				t.Fatal("foreground color changed")
			}
			if mode == "fill" {
				if pixels[0] > 8 || pixels[1] > 8 || pixels[2] > 8 {
					t.Fatal("fill background not black")
				}
			} else if pixels[0] < 200 {
				t.Fatal("crop/blur background missing")
			}
		})
	}
}
func TestPositionedCropSelectsExpectedPixels(t *testing.T) {
	source := "color=c=red:s=400x200:r=30,drawbox=x=200:y=0:w=200:h=200:color=blue:t=fill"
	for _, position := range []float64{0, 1} {
		filter, err := planner.VerticalFilter("crop", 400, 200, 100, 100, position)
		if err != nil {
			t.Fatal(err)
		}
		pixels := render(t, source, filter, 100, 100)
		center := (50*100 + 50) * 3
		if position == 0 && (pixels[center] < 200 || pixels[center+2] > 50) {
			t.Fatal("left crop not red")
		}
		if position == 1 && (pixels[center+2] < 200 || pixels[center] > 50) {
			t.Fatal("right crop not blue")
		}
	}
}
