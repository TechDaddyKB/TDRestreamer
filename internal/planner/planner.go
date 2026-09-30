// Package planner produces deterministic, explainable rendition proposals.
package planner

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"sort"
)

type Media struct {
	Width       int    `json:"width"`
	Height      int    `json:"height"`
	FPS         int    `json:"fps"`
	VideoCodec  string `json:"video_codec"`
	AudioCodec  string `json:"audio_codec"`
	AudioTracks []int  `json:"audio_tracks"`
	Verified    bool   `json:"verified"`
}
type Rectangle struct {
	X      int `json:"x"`
	Y      int `json:"y"`
	Width  int `json:"width"`
	Height int `json:"height"`
}

func (r Rectangle) Validate(w, h int) error {
	if r.X < 0 || r.Y < 0 || r.Width <= 0 || r.Height <= 0 || r.Width > w || r.Height > h || r.X > w-r.Width || r.Y > h-r.Height {
		return errors.New("rectangle exceeds canvas")
	}
	if r.X%2 != 0 || r.Y%2 != 0 || r.Width%2 != 0 || r.Height%2 != 0 {
		return errors.New("rectangle must align to even chroma coordinates")
	}
	return nil
}

type Target struct {
	ID             string     `json:"id"`
	InputID        string     `json:"input_id"`
	Width          int        `json:"width"`
	Height         int        `json:"height"`
	FPS            int        `json:"fps"`
	Bitrate        int        `json:"bitrate_kbps"`
	VideoCodec     string     `json:"video_codec"`
	AudioCodec     string     `json:"audio_codec"`
	AudioTrack     int        `json:"audio_track"`
	Transform      string     `json:"transform"`
	Crop           *Rectangle `json:"crop,omitempty"`
	AllowTranscode bool       `json:"allow_transcode"`
}
type Request struct {
	Input        Media    `json:"input"`
	Targets      []Target `json:"targets"`
	RuleRevision string   `json:"rule_revision"`
}
type Result struct {
	DestinationID string `json:"destination_id"`
	Category      string `json:"category"`
	Reason        string `json:"reason"`
	RenditionID   string `json:"rendition_id,omitempty"`
}
type Plan struct {
	RuleRevision string   `json:"rule_revision"`
	Results      []Result `json:"results"`
	Renditions   int      `json:"renditions"`
}

func Evaluate(req Request) (Plan, error) {
	p := Plan{RuleRevision: req.RuleRevision, Results: []Result{}}
	if req.RuleRevision == "" || req.Input.Width <= 0 || req.Input.Height <= 0 || req.Input.FPS <= 0 || len(req.Targets) > 100 {
		return p, errors.New("invalid input or rule revision")
	}
	seen := map[string]bool{}
	groups := map[string]bool{}
	for _, target := range req.Targets {
		if target.ID == "" || seen[target.ID] {
			return p, errors.New("target identifiers must be unique")
		}
		seen[target.ID] = true
		r := Result{DestinationID: target.ID, Category: "unsupported"}
		if !req.Input.Verified {
			r.Category = "not_verified"
			r.Reason = "Observe input before validating compatibility"
			p.Results = append(p.Results, r)
			continue
		}
		if target.Width <= 0 || target.Height <= 0 || target.Width > 8192 || target.Height > 8192 || target.Width%2 != 0 || target.Height%2 != 0 || target.FPS <= 0 || target.FPS > 120 || target.Bitrate <= 0 || target.Bitrate > 200000 {
			return p, errors.New("invalid output geometry, frame rate or bitrate")
		}
		track := false
		for _, n := range req.Input.AudioTracks {
			if n == target.AudioTrack {
				track = true
			}
		}
		if !track {
			r.Reason = "Selected audio track is absent; no substitution is allowed"
			p.Results = append(p.Results, r)
			continue
		}
		if target.VideoCodec != "h264" || target.AudioCodec != "aac" {
			r.Reason = "Only the generic H.264/AAC profile has a local rule implementation"
			p.Results = append(p.Results, r)
			continue
		}
		switch target.Transform {
		case "", "none", "crop", "fill", "blur":
		default:
			return p, errors.New("unknown transform")
		}
		if target.Crop != nil {
			if err := target.Crop.Validate(req.Input.Width, req.Input.Height); err != nil {
				return p, err
			}
		}
		convert := target.Crop != nil || (target.Transform != "" && target.Transform != "none") || target.Width != req.Input.Width || target.Height != req.Input.Height || target.FPS != req.Input.FPS || target.VideoCodec != req.Input.VideoCodec
		if convert && !target.AllowTranscode {
			r.Reason = "Video conversion requires profile approval"
			p.Results = append(p.Results, r)
			continue
		}
		r.Category = "direct_copy"
		r.Reason = "Geometry and codecs match; destination bitrate/GOP acceptance still requires observation"
		if target.AudioCodec != req.Input.AudioCodec {
			r.Category = "audio_conversion"
			r.Reason = "Selected audio needs conversion"
		}
		if convert {
			r.Category = "video_conversion"
			r.Reason = "Requested geometry, transform or codec requires encoding"
		}
		key := target
		key.ID = ""
		key.AllowTranscode = false
		// Source identity, geometry, transform and audio mapping prevent unsafe sharing.
		raw, _ := json.Marshal(key)
		sum := sha256.Sum256(raw)
		r.RenditionID = hex.EncodeToString(sum[:])
		groups[r.RenditionID] = true
		p.Results = append(p.Results, r)
	}
	sort.Slice(p.Results, func(i, j int) bool { return p.Results[i].DestinationID < p.Results[j].DestinationID })
	p.Renditions = len(groups)
	return p, nil
}

// VerticalFilter only accepts validated numbers, never arbitrary user filter text.
func VerticalFilter(mode string, iw, ih, ow, oh int, position float64) (string, error) {
	if iw <= 0 || ih <= 0 || ow <= 0 || oh <= 0 || ow%2 != 0 || oh%2 != 0 || math.IsNaN(position) || math.IsInf(position, 0) || position < 0 || position > 1 {
		return "", errors.New("invalid transform geometry")
	}
	switch mode {
	case "crop":
		cw, ch := iw, ih
		if iw*oh > ih*ow {
			cw = ih * ow / oh
		} else {
			ch = iw * oh / ow
		}
		cw -= cw % 2
		ch -= ch % 2
		x := int(float64(iw-cw) * position)
		x -= x % 2
		y := (ih - ch) / 2
		y -= y % 2
		if cw < 2 || ch < 2 {
			return "", errors.New("crop is too small")
		}
		return fmt.Sprintf("crop=%d:%d:%d:%d,scale=%d:%d", cw, ch, x, y, ow, oh), nil
	case "fill":
		return fmt.Sprintf("scale=%d:%d:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=%d:%d:(ow-iw)/2:(oh-ih)/2", ow, oh, ow, oh), nil
	case "blur":
		return fmt.Sprintf("split[bg][fg];[bg]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,boxblur=20:2[background];[fg]scale=%d:%d:force_original_aspect_ratio=decrease:force_divisible_by=2[foreground];[background][foreground]overlay=(W-w)/2:(H-h)/2", ow, oh, ow, oh, ow, oh), nil
	default:
		return "", errors.New("unknown vertical mode")
	}
}
