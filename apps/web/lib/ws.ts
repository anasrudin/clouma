// lib/ws.ts
// WebSocket client helpers for the Clouma session stream.
//
// Phase 4B: endpoint renamed from /stream to /ws to match ADK Runner integration.
// The new protocol requires an init message before user input is sent.
//
// Usage:
//   const disconnect = connectSessionStream(sessionId, agentId, onMessage, onClose)
//   // onMessage receives AdkEvent JSON objects
//   // call disconnect() to close the connection

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"

export interface WsInitOptions {
  agentId: string
  userId?: string
  appName?: string
}

type MessageHandler = (data: unknown) => void

/**
 * Connect to the ADK Runner WebSocket stream for a session.
 *
 * Automatically sends the required init message on open.
 * Returns a cleanup function that closes the socket.
 */
export interface SessionConnection {
  disconnect: () => void
  send: (input: string) => void
}

export function connectSessionStream(
  sessionId: string,
  init: WsInitOptions,
  onMessage: MessageHandler,
  onClose?: () => void
): SessionConnection {
  const ws = new WebSocket(`${WS_BASE}/v1/sessions/${sessionId}/ws`)

  ws.onopen = () => {
    ws.send(JSON.stringify({
      agent_id: init.agentId,
      user_id: init.userId ?? "default-user",
      app_name: init.appName ?? "clouma",
    }))
  }

  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)) }
    catch (err) {
      console.warn("[ws] Failed to parse frame:", e.data, err)
    }
  }
  ws.onclose = () => onClose?.()
  ws.onerror = () => ws.close()

  return {
    disconnect: () => ws.close(),
    send: (input: string) => sendInput(ws, input),
  }
}

/**
 * Send a user input message to an already-open WebSocket.
 * The caller is responsible for keeping a reference to the socket.
 */
export function sendInput(ws: WebSocket, input: string): void {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ input }))
  }
}
