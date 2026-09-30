package scheduler

import (
	"testing"
	"time"
)

func TestFencing(t *testing.T) {
	now := time.Now()
	l := Lease{"worker", 2, now.Add(time.Second)}
	if !l.Valid("worker", 2, now) || l.Valid("worker", 1, now) || l.Valid("other", 2, now) || l.Valid("worker", 2, l.Expires) {
		t.Fatal("lease fence")
	}
}
func TestCapacity(t *testing.T) {
	p := Pool{Devices: []Device{{"a", "qsv", 2, 0, true}, {"b", "qsv", 2, 0, true}, {"c", "nvenc", 20, 0, false}}}
	a, _ := p.Reserve("1", "qsv", 2)
	b, _ := p.Reserve("2", "qsv", 2)
	if a == b {
		t.Fatal("not multi-device")
	}
	if _, e := p.Reserve("3", "qsv", 1); e == nil {
		t.Fatal("overcommitted")
	}
	if _, e := p.Reserve("4", "nvenc", 1); e == nil {
		t.Fatal("unverified device")
	}
}
func TestReservationReplayAndRelease(t *testing.T) {
	p := Pool{Devices: []Device{{"a", "qsv", 2, 0, true}}}
	a, e := p.Reserve("job", "qsv", 2)
	if e != nil {
		t.Fatal(e)
	}
	b, e := p.Reserve("job", "qsv", 2)
	if e != nil || a != b || p.Devices[0].Reserved != 2 {
		t.Fatal("duplicate reservation")
	}
	if _, e = p.Reserve("job", "qsv", 1); e == nil {
		t.Fatal("conflicting replay")
	}
	p.Release("job")
	p.Release("job")
	if p.Devices[0].Reserved != 0 {
		t.Fatal("release not idempotent")
	}
}
