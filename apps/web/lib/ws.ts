// lib/ws.ts
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"

type MessageHandler = (data: unknown) => void

export function connectSessionStream(
  sessionId: string,
  onMessage: MessageHandler,
  onClose?: () => void
): () => void {
  const ws = new WebSocket(`${WS_BASE}/v1/sessions/${sessionId}/stream`)
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)) } catch {}
  }
  ws.onclose = () => onClose?.()
  ws.onerror = () => ws.close()
  return () => ws.close()
}
