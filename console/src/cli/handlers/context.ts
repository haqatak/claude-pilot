/**
 * Context Handler - SessionStart
 *
 * Extracted from context-hook.ts - calls worker to generate context.
 * Returns context as hookSpecificOutput for Claude Code to inject.
 */

import type { EventHandler, NormalizedHookInput, HookResult } from "../types.js";
import { getWorkerEndpointConfig } from "../../shared/remote-endpoint.js";
import { fetchWithAuth } from "../../shared/fetch-with-auth.js";
import { getProjectContext } from "../../utils/project-name.js";
import { logger } from "../../utils/logger.js";

export const contextHandler: EventHandler = {
  async execute(input: NormalizedHookInput): Promise<HookResult> {
    if (process.env.CLAUDE_PILOT_NO_CONTEXT === "1" || process.env.CLAUDE_PILOT_NO_CONTEXT === "true") {
      return {
        hookSpecificOutput: {
          hookEventName: "SessionStart",
          additionalContext: "",
        },
      };
    }

    const endpointConfig = getWorkerEndpointConfig();
    const cwd = input.cwd ?? process.cwd();
    const context = getProjectContext(cwd);

    const projectsParam = context.allProjects.join(",");
    const url = `${endpointConfig.baseUrl}/api/context/inject?projects=${encodeURIComponent(projectsParam)}`;

    const response = await fetchWithAuth(url, undefined, { endpointConfig });

    if (!response.ok) {
      throw new Error(`Context generation failed: ${response.status}`);
    }

    const result = await response.text();
    const additionalContext = result.trim();

    return {
      hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext,
      },
    };
  },
};
