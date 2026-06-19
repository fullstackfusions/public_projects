package handlers

import (
	"bufio"
	"encoding/json"
	"fmt"
)

// sseSend writes a single SSE event frame to the response writer.
func sseSend(w *bufio.Writer, event string, data any) {
	b, err := json.Marshal(data)
	if err != nil {
		return
	}
	fmt.Fprintf(w, "event: %s\n", event)
	fmt.Fprintf(w, "data: %s\n\n", b)
	w.Flush()
}
