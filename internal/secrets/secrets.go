// Package secrets implements scoped envelope encryption and one-time tokens.
package secrets

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
)

func Token() (string, error) {
	b := make([]byte, 32)
	_, err := rand.Read(b)
	return base64.RawURLEncoding.EncodeToString(b), err
}
func Hash(token string) []byte { v := sha256.Sum256([]byte(token)); return v[:] }
func seal(key, plaintext, aad []byte) ([]byte, error) {
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	g, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	nonce := make([]byte, g.NonceSize())
	if _, err = rand.Read(nonce); err != nil {
		return nil, err
	}
	return g.Seal(nonce, nonce, plaintext, aad), nil
}
func open(key, data, aad []byte) ([]byte, error) {
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	g, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	if len(data) < g.NonceSize()+g.Overhead() {
		return nil, errors.New("invalid encrypted envelope")
	}
	return g.Open(nil, data[:g.NonceSize()], data[g.NonceSize():], aad)
}

type Envelope struct {
	KeyID      string `json:"key_id"`
	WrappedKey []byte `json:"wrapped_key"`
	Ciphertext []byte `json:"ciphertext"`
}

func Encrypt(keyID string, root, plaintext []byte, scope string) (Envelope, error) {
	if len(root) != 32 || keyID == "" || scope == "" {
		return Envelope{}, errors.New("invalid encryption configuration")
	}
	dataKey := make([]byte, 32)
	if _, err := rand.Read(dataKey); err != nil {
		return Envelope{}, err
	}
	wrapped, err := seal(root, dataKey, []byte(scope))
	if err != nil {
		return Envelope{}, err
	}
	ciphertext, err := seal(dataKey, plaintext, []byte(scope))
	return Envelope{keyID, wrapped, ciphertext}, err
}
func Decrypt(keys map[string][]byte, e Envelope, scope string) ([]byte, error) {
	key, ok := keys[e.KeyID]
	if !ok {
		return nil, errors.New("unknown encryption key")
	}
	dataKey, err := open(key, e.WrappedKey, []byte(scope))
	if err != nil {
		return nil, errors.New("invalid encrypted envelope")
	}
	return open(dataKey, e.Ciphertext, []byte(scope))
}
