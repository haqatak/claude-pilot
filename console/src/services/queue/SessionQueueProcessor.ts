import { EventEmitter } from "events";
import { PendingMessageStore, PersistentPendingMessage } from "../sqlite/PendingMessageStore.js";
import type { PendingMessageWithId } from "../worker-types.js";
import { logger } from "../../utils/logger.js";

export class SessionQueueProcessor {
  constructor(
    private store: PendingMessageStore,
    private events: EventEmitter,
  ) {}

  /**
   * Create an async iterator that yields messages as they become available.
   * Uses atomic claim-and-delete to prevent duplicates.
   * The queue is a pure buffer: claim it, delete it, process in memory.
   * Waits for 'message' event when queue is empty.
   */
  async *createIterator(sessionDbId: number, signal: AbortSignal): AsyncIterableIterator<PendingMessageWithId> {
    while (!signal.aborted) {
      try {
        const persistentMessage = this.store.claimAndDelete(sessionDbId);

        if (persistentMessage) {
          yield this.toPendingMessageWithId(persistentMessage);
        } else {
          await this.waitForMessage(signal);
        }
      } catch (error) {
        if (signal.aborted) return;
        logger.error("SESSION", "Error in queue processor loop", { sessionDbId }, error as Error);
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }
  }

  private toPendingMessageWithId(msg: PersistentPendingMessage): PendingMessageWithId {
    const pending = this.store.toPendingMessage(msg);
    return {
      ...pending,
      _persistentId: msg.id,
      _originalTimestamp: msg.created_at_epoch,
    };
  }

  private waitForMessage(signal: AbortSignal): Promise<void> {
    return new Promise<void>((resolve) => {
      const onMessage = () => {
        cleanup();
        resolve();
      };

      const onAbort = () => {
        cleanup();
        resolve();
      };

      const cleanup = () => {
        this.events.off("message", onMessage);
        signal.removeEventListener("abort", onAbort);
      };

      this.events.once("message", onMessage);
      signal.addEventListener("abort", onAbort, { once: true });
    });
  }
}
