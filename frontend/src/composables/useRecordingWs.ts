import { ref, shallowRef } from 'vue'

export interface RecordingState {
  status: 'idle' | 'connecting' | 'recording' | 'stopped'
  frameCount: number
}

export interface UserEvent {
  type: 'click' | 'dblclick' | 'type' | 'keypress' | 'scroll' | 'navigate'
  x?: number
  y?: number
  text?: string
  key?: string
  deltaX?: number
  deltaY?: number
  url?: string
}

export function useRecordingWs() {
  const canvasRef = shallowRef<HTMLCanvasElement | null>(null)
  const state = ref<RecordingState>({ status: 'idle', frameCount: 0 })
  let ws: WebSocket | null = null
  let img: HTMLImageElement | null = null

  function connect(wsUrl: string) {
    return new Promise<void>((resolve, reject) => {
      state.value = { status: 'connecting', frameCount: 0 }
      ws = new WebSocket(wsUrl)
      ws.binaryType = 'arraybuffer'

      ws.onopen = () => {
        state.value.status = 'recording'
        resolve()
      }

      ws.onerror = () => {
        state.value.status = 'idle'
        reject(new Error('WebSocket connection failed'))
      }

      ws.onmessage = (event: MessageEvent) => {
        const canvas = canvasRef.value
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        if (!ctx) return

        const blob = new Blob([event.data], { type: 'image/jpeg' })
        const url = URL.createObjectURL(blob)

        if (!img) {
          img = new Image()
        }
        img.onload = () => {
          canvas.width = img!.width
          canvas.height = img!.height
          ctx!.drawImage(img!, 0, 0)
          URL.revokeObjectURL(url)
          state.value.frameCount++
        }
        img.src = url
      }

      ws.onclose = () => {
        if (state.value.status === 'recording') {
          state.value.status = 'stopped'
        }
      }
    })
  }

  function sendEvent(event: UserEvent) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(event))
    }
  }

  function stop() {
    if (ws) {
      ws.send(JSON.stringify({ type: 'stop' }))
      ws.close()
      ws = null
    }
    state.value.status = 'stopped'
  }

  function cleanup() {
    if (ws) {
      ws.close()
      ws = null
    }
    img = null
    state.value = { status: 'idle', frameCount: 0 }
  }

  return {
    canvasRef,
    state,
    connect,
    sendEvent,
    stop,
    cleanup,
  }
}
