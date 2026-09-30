package scheduler

import (
	"errors"
	"sync"
	"time"
)

// Lease authority is persisted by the store; workers use this deadline guard locally.
type Lease struct {
	Owner   string
	Epoch   int64
	Expires time.Time
}

func (l Lease) Valid(owner string, epoch int64, now time.Time) bool {
	return owner != "" && l.Owner == owner && l.Epoch == epoch && now.Before(l.Expires)
}

type Device struct {
	ID       string
	Backend  string
	Capacity int
	Reserved int
	Verified bool
}
type reservation struct {
	device  int
	units   int
	backend string
}
type Pool struct {
	mu      sync.Mutex
	Devices []Device
	jobs    map[string]reservation
}

func (p *Pool) Reserve(job, backend string, units int) (string, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if job == "" || units <= 0 {
		return "", errors.New("invalid reservation")
	}
	if p.jobs == nil {
		p.jobs = map[string]reservation{}
	}
	if prior, ok := p.jobs[job]; ok {
		if prior.units != units || prior.backend != backend {
			return "", errors.New("reservation conflicts with existing job")
		}
		return p.Devices[prior.device].ID, nil
	}
	best := -1
	for i, d := range p.Devices {
		if d.Verified && d.Backend == backend && d.Capacity-d.Reserved >= units && (best < 0 || d.Reserved < p.Devices[best].Reserved) {
			best = i
		}
	}
	if best < 0 {
		return "", errors.New("insufficient verified capacity")
	}
	p.Devices[best].Reserved += units
	p.jobs[job] = reservation{best, units, backend}
	return p.Devices[best].ID, nil
}
func (p *Pool) Release(job string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if r, ok := p.jobs[job]; ok {
		p.Devices[r.device].Reserved -= r.units
		delete(p.jobs, job)
	}
}
