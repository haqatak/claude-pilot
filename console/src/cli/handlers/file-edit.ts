/**
 * File Edit Handler - afterFileEdit hook
 *
 * Handles file edit observations.
 * Similar to observation handler but with file-specific metadata.
 */

import type { EventHandler, NormalizedHookInput, HookResult } from "../types.js";
import { tryEnsureWorkerRunning, getWorkerBaseUrl } from "../../shared/worker-utils.js";
import { fetchWithRetry } from "../../shared/fetch-utils.js";
import { isProjectExcluded, isMemoryDisabledByProjectConfig } from "../../shared/project-exclusion.js";
import { getProjectName } from "../../utils/project-name.js";
import { logger } from "../../utils/logger.js";

export const fileEditHandler: EventHandler = {
  async execute(input: NormalizedHookInput): Promise<HookResult> {
    const workerStatus = await tryEnsureWorkerRunning(2000);
    if (!workerStatus.ready) {
      logger.debug("HOOK", "file-edit: Worker not ready, skipping file edit observation", {
        waited: workerStatus.waited,
      });
      return { continue: true, suppressOutput: true };
    }

    const { sessionId, cwd, filePath, edits } = input;

    if (!filePath) {
      throw new Error("fileEditHandler requires filePath");
    }

    if (isMemoryDisabledByProjectConfig(cwd)) {
      logger.debug("HOOK", "file-edit: Memory disabled by .pilot/memory.json", { cwd });
      return { continue: true, suppressOutput: true };
    }

    const project = getProjectName(cwd);
    if (isProjectExcluded(project)) {
      logger.debug("HOOK", "file-edit: Project excluded by CLAUDE_PILOT_EXCLUDE_PROJECTS", { project });
      return { continue: true, suppressOutput: true };
    }

    const baseUrl = getWorkerBaseUrl();

    logger.dataIn("HOOK", `FileEdit: ${filePath}`, {
      workerUrl: baseUrl,
      editCount: edits?.length ?? 0,
    });

    if (!cwd) {
      throw new Error(`Missing cwd in FileEdit hook input for session ${sessionId}, file ${filePath}`);
    }

    const response = await fetchWithRetry(`${baseUrl}/api/sessions/observations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contentSessionId: sessionId,
        tool_name: "write_file",
        tool_input: { filePath, edits },
        tool_response: { success: true },
        cwd,
      }),
    });

    if (!response.ok) {
      throw new Error(`File edit observation storage failed: ${response.status}`);
    }

    logger.debug("HOOK", "File edit observation sent successfully", { filePath });

    return { continue: true, suppressOutput: true };
  },
};
