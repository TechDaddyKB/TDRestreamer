package auth

import "testing"

func TestPermissions(t *testing.T) {
	for _, role := range []string{"admin", "streamer", "operator", "viewer", "unknown"} {
		p := Principal{UserID: "u", TenantID: "a", Role: role}
		for _, act := range []string{"view", "operate", "edit", "secrets", "members", "infrastructure", "reveal"} {
			if p.Allows("b", act) {
				t.Fatalf("cross tenant %s %s", role, act)
			}
			if p.Allows("a", "reveal") {
				t.Fatal("reveal allowed")
			}
		}
	}
	p := Principal{UserID: "u", TenantID: "a", Role: "operator"}
	if !p.Allows("a", "operate") || p.Allows("a", "edit") {
		t.Fatal("operator defaults")
	}
	p.EditGranted = true
	if !p.Allows("a", "edit") || p.Allows("a", "secrets") {
		t.Fatal("delegation scope")
	}
	if (Principal{}).Allows("", "view") {
		t.Fatal("anonymous")
	}
}
