package sessions

import "testing"

func TestSafety(t *testing.T) {
	for _, state := range []State{Idle, Preparing, Waiting, Testing, Armed, Starting, Live, Degraded, Stopping, Ended, Failed} {
		if MayPublish(state, "test") {
			t.Fatal("test publish", state)
		}
	}
	s, e := Transition(Idle, "test")
	if e != nil || s != Testing {
		t.Fatal(s, e)
	}
	if _, e = Transition(s, "online"); e == nil {
		t.Fatal("test went live without explicit action")
	}
	s, e = Transition(s, "go-live")
	if e != nil || s != Starting {
		t.Fatal(s, e)
	}
	s, _ = Transition(s, "stop")
	if MayPublish(s, "live") {
		t.Fatal("stop permits retry")
	}
	s, _ = Transition(s, "stopped")
	again, _ := Transition(s, "stop")
	if again != Ended {
		t.Fatal("stop not idempotent")
	}
}
