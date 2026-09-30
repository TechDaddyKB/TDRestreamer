package planner

import (
	"math"
	"testing"
)

func TestPlanSharingAndSafety(t *testing.T) {
	target := Target{ID: "a", InputID: "horizontal", Width: 1920, Height: 1080, FPS: 30, Bitrate: 6000, VideoCodec: "h264", AudioCodec: "aac", AudioTrack: 1}
	other := target
	other.ID = "b"
	req := Request{Input: Media{1920, 1080, 30, "h264", "aac", []int{1, 2}, true}, Targets: []Target{target, other}, RuleRevision: "generic-v1"}
	p, e := Evaluate(req)
	if e != nil || p.Renditions != 1 || p.Results[0].Category != "direct_copy" {
		t.Fatal(p, e)
	}
	req.Targets[1].AudioTrack = 2
	p, _ = Evaluate(req)
	if p.Renditions != 2 {
		t.Fatal("different audio shared")
	}
	req.Targets[1].AudioTrack = 3
	p, _ = Evaluate(req)
	if p.Results[1].Category != "unsupported" {
		t.Fatal("missing track replaced")
	}
	req.Targets[0].Width = 1080
	req.Targets[0].Height = 1920
	p, _ = Evaluate(req)
	if p.Results[0].Category != "unsupported" {
		t.Fatal("unapproved conversion")
	}
	req.Targets[0].AllowTranscode = true
	p, _ = Evaluate(req)
	if p.Results[0].Category != "video_conversion" {
		t.Fatal(p)
	}
	req.Input.Verified = false
	p, _ = Evaluate(req)
	if p.Renditions != 0 {
		t.Fatal("unverified input approved")
	}
}
func TestGeometry(t *testing.T) {
	for _, r := range []Rectangle{{-1, 0, 10, 10}, {0, 0, 1922, 1080}, {1, 0, 10, 10}, {0, 0, 0, 2}, {math.MaxInt, 0, 2, 2}} {
		if r.Validate(1920, 1080) == nil {
			t.Fatal(r)
		}
	}
	if (Rectangle{0, 0, 1920, 1080}).Validate(1920, 1080) != nil {
		t.Fatal("valid rectangle")
	}
	for _, mode := range []string{"crop", "fill", "blur"} {
		if _, e := VerticalFilter(mode, 1920, 1080, 1080, 1920, 0.5); e != nil {
			t.Fatal(e)
		}
	}
	if _, e := VerticalFilter("crop", 1920, 1080, 1080, 1920, math.NaN()); e == nil {
		t.Fatal("NaN accepted")
	}
}
