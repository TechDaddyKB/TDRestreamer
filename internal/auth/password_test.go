package auth

import "testing"

func TestPasswordHash(t *testing.T) {
	h, e := PasswordHash("a sufficiently long password")
	if e != nil {
		t.Fatal(e)
	}
	if !PasswordMatches(h, "a sufficiently long password") || PasswordMatches(h, "wrong") {
		t.Fatal("password verification")
	}
	other, e := PasswordHash("a sufficiently long password")
	if e != nil || other == h {
		t.Fatal("salts not independent")
	}
	if _, e = PasswordHash("short"); e == nil {
		t.Fatal("short password")
	}
	for _, bad := range []string{"", "$", "argon2id-v1$a$b", "argon2id-v2$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"} {
		if PasswordMatches(bad, "anything") {
			t.Fatal("malformed accepted")
		}
	}
}
