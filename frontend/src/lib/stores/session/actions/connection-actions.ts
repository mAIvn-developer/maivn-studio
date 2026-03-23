import { connectToEvents } from "$lib/api_client/sessions";

import { handleSessionStreamError } from "./action-helpers";
import type { SessionStoreContext } from "../types";

const MAX_TRACKED_EVENT_IDS = 1024;

export function createConnectToEventStream(
  ctx: SessionStoreContext,
  disconnect: () => void,
  handleEvent: (type: string, data: unknown) => void,
  getEventSource: () => EventSource | null,
  setEventSource: (es: EventSource | null) => void,
) {
  // Track the last server event ID so reconnects can resume from where the
  // client left off.  The backend's EventBridge.generate_sse(last_event_id)
  // skips already-seen history, eliminating duplicate messages/cards.
  let lastSeenEventId: string | undefined;
  let lastConnectedSessionId: string | undefined;
  let connectionGeneration = 0;
  const seenEventIds = new Set<string>();
  const seenEventIdOrder: string[] = [];

  function rememberEventId(eventId: string) {
    if (seenEventIds.has(eventId)) {
      return;
    }

    seenEventIds.add(eventId);
    seenEventIdOrder.push(eventId);

    if (seenEventIdOrder.length <= MAX_TRACKED_EVENT_IDS) {
      return;
    }

    const removedEventId = seenEventIdOrder.shift();
    if (removedEventId) {
      seenEventIds.delete(removedEventId);
    }
  }

  return function connectToEventStream(sessionId: string) {
    if (lastConnectedSessionId !== sessionId) {
      lastSeenEventId = undefined;
      seenEventIds.clear();
      seenEventIdOrder.length = 0;
    }
    lastConnectedSessionId = sessionId;
    connectionGeneration += 1;
    const activeGeneration = connectionGeneration;

    // Close existing connection
    disconnect();

    let es: EventSource | null = null;
    es = connectToEvents(
      sessionId,
      (event) => {
        if (activeGeneration !== connectionGeneration || getEventSource() !== es) {
          return;
        }

        // Track the latest server event ID for future reconnects.
        if (event.eventId) {
          if (seenEventIds.has(event.eventId)) {
            return;
          }
          rememberEventId(event.eventId);
          lastSeenEventId = event.eventId;
        }
        handleEvent(event.type, event.data);
      },
      (e) => {
        if (activeGeneration !== connectionGeneration || getEventSource() !== es) {
          return;
        }
        handleSessionStreamError(ctx, getEventSource, e);
      },
      lastSeenEventId,
    );

    setEventSource(es);
  };
}

export function createDisconnect(
  ctx: SessionStoreContext,
  getEventSource: () => EventSource | null,
  setEventSource: (es: EventSource | null) => void,
  clearMemoryIndexedToastTimer: () => void,
) {
  return function disconnect() {
    // Flush pending updates before disconnecting
    ctx.flushPendingStreams();
    ctx.setStreamingAssistantItemId(null);
    clearMemoryIndexedToastTimer();
    ctx.setMemoryIndexedToast(null);

    const es = getEventSource();
    if (es) {
      es.close();
      setEventSource(null);
    }
  };
}
