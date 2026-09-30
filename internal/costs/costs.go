package costs

import (
	"errors"
	"math"
)

type Tier struct {
	UpToGB float64
	PerGB  float64
}

func Egress(bytes uint64, allowanceGB float64, tiers []Tier) (float64, error) {
	if allowanceGB < 0 || math.IsNaN(allowanceGB) || math.IsInf(allowanceGB, 0) || len(tiers) == 0 {
		return 0, errors.New("invalid pricing")
	}
	remaining := math.Max(0, float64(bytes)/1e9-allowanceGB)
	total, previous := 0.0, 0.0
	for i, t := range tiers {
		if math.IsNaN(t.UpToGB) || math.IsInf(t.UpToGB, 0) || math.IsNaN(t.PerGB) || math.IsInf(t.PerGB, 0) || t.PerGB < 0 || t.UpToGB < 0 || (t.UpToGB == 0 && i != len(tiers)-1) || (t.UpToGB != 0 && t.UpToGB <= previous) {
			return 0, errors.New("invalid pricing tier")
		}
		used := remaining
		if t.UpToGB != 0 {
			used = math.Min(used, t.UpToGB-previous)
		}
		total += used * t.PerGB
		remaining -= used
		previous = t.UpToGB
	}
	if remaining > 0 {
		return 0, errors.New("pricing does not cover usage")
	}
	return total, nil
}
