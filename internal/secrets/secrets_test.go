package secrets

import (
	"bytes"
	"testing"
)

func TestEnvelopeScopeAndRotation(t *testing.T) {
	old := bytes.Repeat([]byte{1}, 32)
	next := bytes.Repeat([]byte{2}, 32)
	e, err := Encrypt("v1", old, []byte("credential"), "tenant-a/destination-a")
	if err != nil {
		t.Fatal(err)
	}
	keys := map[string][]byte{"v1": old, "v2": next}
	clear, err := Decrypt(keys, e, "tenant-a/destination-a")
	if err != nil || string(clear) != "credential" {
		t.Fatal(err)
	}
	if _, err = Decrypt(keys, e, "tenant-b/destination-a"); err == nil {
		t.Fatal("cross-tenant decrypt")
	}
	rotated, err := Encrypt("v2", next, clear, "tenant-a/destination-a")
	if err != nil {
		t.Fatal(err)
	}
	delete(keys, "v1")
	if _, err = Decrypt(keys, rotated, "tenant-a/destination-a"); err != nil {
		t.Fatal(err)
	}
	rotated.Ciphertext[len(rotated.Ciphertext)-1] ^= 1
	if _, err = Decrypt(keys, rotated, "tenant-a/destination-a"); err == nil {
		t.Fatal("tamper accepted")
	}
}
func TestTokens(t *testing.T) {
	a, _ := Token()
	b, _ := Token()
	if len(a) < 40 || a == b || bytes.Equal(Hash(a), Hash(b)) {
		t.Fatal("token entropy")
	}
}
