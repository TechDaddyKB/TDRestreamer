package costs

import (
	"math"
	"testing"
)

func TestTieredDecimalBytes(t *testing.T) {
	v, e := Egress(250_000_000_000, 50, []Tier{{100, 0.1}, {0, 0.05}})
	if e != nil || math.Abs(v-15) > 1e-8 {
		t.Fatal(v, e)
	}
	if _, e = Egress(1, 0, []Tier{{0, -1}}); e == nil {
		t.Fatal("negative tariff")
	}
}
