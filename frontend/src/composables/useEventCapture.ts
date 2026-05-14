import type { UserEvent } from './useRecordingWs'

type SendEventFn = (event: UserEvent) => void

export function useEventCapture(
  canvas: HTMLCanvasElement,
  sendEvent: SendEventFn,
  viewportWidth: number,
  viewportHeight: number,
) {
  function mapCoords(clientX: number, clientY: number) {
    const rect = canvas.getBoundingClientRect()
    const scaleX = viewportWidth / rect.width
    const scaleY = viewportHeight / rect.height
    return {
      x: Math.round((clientX - rect.left) * scaleX),
      y: Math.round((clientY - rect.top) * scaleY),
    }
  }

  function onClick(e: MouseEvent) {
    const { x, y } = mapCoords(e.clientX, e.clientY)
    sendEvent({ type: 'click', x, y })
  }

  function onDblClick(e: MouseEvent) {
    const { x, y } = mapCoords(e.clientX, e.clientY)
    sendEvent({ type: 'dblclick', x, y })
  }

  function onWheel(e: WheelEvent) {
    e.preventDefault()
    sendEvent({ type: 'scroll', deltaX: e.deltaX, deltaY: e.deltaY })
  }

  function onKeyDown(e: KeyboardEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      sendEvent({ type: 'type', text: e.key })
    } else {
      sendEvent({ type: 'keypress', key: e.key })
    }
  }

  canvas.addEventListener('click', onClick)
  canvas.addEventListener('dblclick', onDblClick)
  canvas.addEventListener('wheel', onWheel, { passive: false })
  document.addEventListener('keydown', onKeyDown, true)

  function cleanup() {
    canvas.removeEventListener('click', onClick)
    canvas.removeEventListener('dblclick', onDblClick)
    canvas.removeEventListener('wheel', onWheel)
    document.removeEventListener('keydown', onKeyDown, true)
  }

  return { cleanup }
}
