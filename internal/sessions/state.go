package sessions

import "errors"

type State string

const (
	Idle      State = "idle"
	Preparing State = "preparing"
	Waiting   State = "waiting"
	Testing   State = "testing"
	Armed     State = "armed"
	Starting  State = "starting"
	Live      State = "live"
	Degraded  State = "degraded"
	Stopping  State = "stopping"
	Ended     State = "ended"
	Failed    State = "failed"
)

var ErrTransition = errors.New("invalid session transition")

func Transition(from State, action string) (State, error) {
	switch action {
	case "test":
		if from == Idle || from == Ended || from == Failed || from == Armed {
			return Testing, nil
		}
	case "prepare":
		if from == Idle || from == Ended || from == Failed {
			return Preparing, nil
		}
	case "wait":
		if from == Preparing {
			return Waiting, nil
		}
	case "arm":
		if from == Waiting || from == Preparing {
			return Armed, nil
		}
	case "go-live":
		if from == Testing || from == Armed {
			return Starting, nil
		}
	case "online":
		if from == Starting || from == Degraded {
			return Live, nil
		}
	case "degrade":
		if from == Live {
			return Degraded, nil
		}
	case "stop":
		if from == Ended || from == Idle {
			return from, nil
		}
		return Stopping, nil
	case "stopped":
		if from == Stopping {
			return Ended, nil
		}
	case "fail":
		if from != Ended && from != Idle {
			return Failed, nil
		}
	}
	return from, ErrTransition
}
func MayPublish(state State, mode string) bool {
	return mode == "live" && (state == Starting || state == Live || state == Degraded)
}
