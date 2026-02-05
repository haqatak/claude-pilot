/**
 * Memory Routes
 *
 * Handles manual memory/observation saving.
 * POST /api/memory/save - Save a manual memory observation
 */

import express, { Request, Response } from "express";
import { BaseRouteHandler } from "../BaseRouteHandler.js";
import { logger } from "../../../../utils/logger.js";
import type { DatabaseManager } from "../../DatabaseManager.js";

export class MemoryRoutes extends BaseRouteHandler {
  constructor(
    private dbManager: DatabaseManager,
    private defaultProject: string,
  ) {
    super();
  }

  setupRoutes(app: express.Application): void {
    app.post("/api/memory/save", this.handleSaveMemory.bind(this));
  }

  /**
   * POST /api/memory/save - Save a manual memory/observation
   * Body: { text: string, title?: string, project?: string }
   */
  private handleSaveMemory = this.wrapHandler(async (req: Request, res: Response): Promise<void> => {
    const { text, title, project } = req.body;
    const targetProject = project || this.defaultProject;

    if (!text || typeof text !== "string" || text.trim().length === 0) {
      this.badRequest(res, "text is required and must be non-empty");
      return;
    }

    const sessionStore = this.dbManager.getSessionStore();
    const chromaSync = this.dbManager.getChromaSync();

    const memorySessionId = sessionStore.getOrCreateManualSession(targetProject);

    const observation = {
      type: "discovery",
      title: title || text.substring(0, 60).trim() + (text.length > 60 ? "..." : ""),
      subtitle: "Manual memory",
      facts: [] as string[],
      narrative: text,
      concepts: [] as string[],
      files_read: [] as string[],
      files_modified: [] as string[],
    };

    const result = sessionStore.storeObservation(memorySessionId, targetProject, observation, 0, 0);

    logger.info("MEMORY", "Manual observation saved", {
      id: result.id,
      project: targetProject,
      title: observation.title,
    });

    chromaSync
      .syncObservation(result.id, memorySessionId, targetProject, observation, 0, result.createdAtEpoch, 0)
      .catch((err) => {
        logger.error("MEMORY", "ChromaDB sync failed", { id: result.id }, err as Error);
      });

    res.json({
      success: true,
      id: result.id,
      title: observation.title,
      project: targetProject,
      message: `Memory saved as observation #${result.id}`,
    });
  });
}
