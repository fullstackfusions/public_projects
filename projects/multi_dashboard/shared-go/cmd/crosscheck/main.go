// Cross-language JWT verification tool.
//
// Usage:
//
//	# Verify a token minted elsewhere (e.g. by shared-py)
//	cat /tmp/py_token.txt | go run ./cmd/crosscheck verify
//
//	# Mint a token to be verified by shared-py
//	go run ./cmd/crosscheck mint
//
// The shared secret is read from CROSSCHECK_SECRET env var.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/mihirzz/chatbot-shared-go/auth"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: crosscheck verify|mint")
		os.Exit(2)
	}
	secret := os.Getenv("CROSSCHECK_SECRET")
	if secret == "" {
		fmt.Fprintln(os.Stderr, "CROSSCHECK_SECRET env var required")
		os.Exit(2)
	}

	switch os.Args[1] {
	case "verify":
		scanner := bufio.NewScanner(os.Stdin)
		scanner.Buffer(make([]byte, 0, 64*1024), 64*1024)
		scanner.Scan()
		token := strings.TrimSpace(scanner.Text())
		claims, err := auth.VerifyJWT(token, secret, "HS256", auth.AccessToken)
		if err != nil {
			fmt.Fprintln(os.Stderr, "VERIFY FAILED:", err)
			os.Exit(1)
		}
		out := map[string]any{
			"sub":   claims.Subject,
			"email": claims.Email,
			"name":  claims.Name,
			"role":  claims.Role,
			"type":  claims.Type,
			"jti":   claims.JTI,
		}
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		_ = enc.Encode(out)
	case "mint":
		tok, err := auth.EncodeJWT(
			map[string]any{
				"sub":   "go-2",
				"email": "alice-go@example.com",
				"role":  "user",
			},
			secret, "HS256", 300, auth.AccessToken,
		)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		fmt.Println(tok)
	default:
		fmt.Fprintln(os.Stderr, "unknown command")
		os.Exit(2)
	}
}
