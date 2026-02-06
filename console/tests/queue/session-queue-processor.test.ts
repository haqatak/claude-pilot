import { describe, it, expect, beforeEach } from "bun:test";
import { EventEmitter } from "events";
import { SessionQueueProcessor } from "../../src/services/queue/SessionQueueProcessor.js";

/**
 * Minimal mock for PendingMessageStore.
 * Only implements methods used by SessionQueueProcessor.
 */
function createMockStore(messages: Array<{ id: number; session_id: number; payload: string; created_at_epoch: number }> = []) {
  const queue = [...messages];
  return {
    claimAndDelete(sessionDbId: number) {
      const idx = queue.findIndex((m) => m.session_id === sessionDbId);
      if (idx === -1) return null;
      return queue.splice(idx, 1)[0];
    },
    toPendingMessage(msg: { payload: string }) {
      return JSON.parse(msg.payload);
    },
  };
}

function makeMessage(sessionDbId: number, id = 1) {
  return {
    id,
    session_id: sessionDbId,
    payload: JSON.stringify({ type: "test", content: `msg-${id}` }),
    created_at_epoch: Date.now(),
  };
}

describe("SessionQueueProcessor", () => {
  let events: EventEmitter;
  const SESSION_ID = 42;

  beforeEach(() => {
    events = new EventEmitter();
  });

  describe("waitForMessage (via createIterator)", () => {
    it("yields message when message event fires", async () => {
      const store = createMockStore([]);
      const processor = new SessionQueueProcessor(store as any, events);
      const controller = new AbortController();

      setTimeout(() => {
        store.claimAndDelete = () => makeMessage(SESSION_ID) as any;
        events.emit("message");
      }, 10);
      setTimeout(() => controller.abort(), 50);

      const results: any[] = [];
      for await (const msg of processor.createIterator(SESSION_ID, controller.signal)) {
        results.push(msg);
        controller.abort();
      }

      expect(results.length).toBe(1);
    });

    it("exits when signal is aborted while waiting", async () => {
      const store = createMockStore([]);
      const processor = new SessionQueueProcessor(store as any, events);
      const controller = new AbortController();

      setTimeout(() => controller.abort(), 30);

      const results: any[] = [];
      for await (const msg of processor.createIterator(SESSION_ID, controller.signal)) {
        results.push(msg);
      }

      expect(results.length).toBe(0);
    });
  });

  describe("createIterator", () => {
    it("yields messages normally when queue has items", async () => {
      const store = createMockStore([
        makeMessage(SESSION_ID, 1),
        makeMessage(SESSION_ID, 2),
        makeMessage(SESSION_ID, 3),
      ]);
      const processor = new SessionQueueProcessor(store as any, events);
      const controller = new AbortController();

      const results: any[] = [];
      for await (const msg of processor.createIterator(SESSION_ID, controller.signal)) {
        results.push(msg);
        if (results.length === 3) controller.abort();
      }

      expect(results.length).toBe(3);
    });

    it("waits for event when queue is empty then yields on message", async () => {
      const store = createMockStore([]);
      const processor = new SessionQueueProcessor(store as any, events);
      const controller = new AbortController();

      setTimeout(() => {
        (store as any).claimAndDelete = () => makeMessage(SESSION_ID, 1) as any;
        events.emit("message");
      }, 20);

      const results: any[] = [];
      for await (const msg of processor.createIterator(SESSION_ID, controller.signal)) {
        results.push(msg);
        controller.abort();
      }

      expect(results.length).toBe(1);
    });

    it("exits immediately when signal is pre-aborted", async () => {
      const store = createMockStore([makeMessage(SESSION_ID)]);
      const processor = new SessionQueueProcessor(store as any, events);
      const controller = new AbortController();
      controller.abort();

      const results: any[] = [];
      for await (const msg of processor.createIterator(SESSION_ID, controller.signal)) {
        results.push(msg);
      }

      expect(results.length).toBe(0);
    });

    it("yields multiple messages across events", async () => {
      const store = createMockStore([]);
      const processor = new SessionQueueProcessor(store as any, events);
      const controller = new AbortController();

      setTimeout(() => {
        (store as any).claimAndDelete = () => {
          (store as any).claimAndDelete = () => null;
          return makeMessage(SESSION_ID, 1);
        };
        events.emit("message");
      }, 10);

      setTimeout(() => {
        (store as any).claimAndDelete = () => {
          (store as any).claimAndDelete = () => null;
          return makeMessage(SESSION_ID, 2);
        };
        events.emit("message");
      }, 30);

      setTimeout(() => controller.abort(), 60);

      const results: any[] = [];
      for await (const msg of processor.createIterator(SESSION_ID, controller.signal)) {
        results.push(msg);
      }

      expect(results.length).toBe(2);
    });
  });
});
