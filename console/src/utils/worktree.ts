/**
 * Worktree Detection Utility
 *
 * Detects if the current working directory is a git worktree and extracts
 * information about the parent repository.
 *
 * Git worktrees have a `.git` file (not directory) containing:
 *   gitdir: /path/to/parent/.git/worktrees/<name>
 */

import { statSync, readFileSync } from "fs";
import path from "path";

export interface WorktreeInfo {
  isWorktree: boolean;
  worktreeName: string | null;
  parentRepoPath: string | null;
  parentProjectName: string | null;
}

const NOT_A_WORKTREE: WorktreeInfo = {
  isWorktree: false,
  worktreeName: null,
  parentRepoPath: null,
  parentProjectName: null,
};

/**
 * Detect if a directory is a git worktree and extract parent info.
 *
 * @param cwd - Current working directory (absolute path)
 * @returns WorktreeInfo with parent details if worktree, otherwise isWorktree=false
 */
export function detectWorktree(cwd: string): WorktreeInfo {
  const gitPath = path.join(cwd, ".git");

  let stat;
  try {
    stat = statSync(gitPath);
  } catch {
    return NOT_A_WORKTREE;
  }

  if (!stat.isFile()) {
    return NOT_A_WORKTREE;
  }

  let content: string;
  try {
    content = readFileSync(gitPath, "utf-8").trim();
  } catch {
    return NOT_A_WORKTREE;
  }

  const match = content.match(/^gitdir:\s*(.+)$/);
  if (!match) {
    return NOT_A_WORKTREE;
  }

  const gitdirPath = match[1];

  const worktreesMatch = gitdirPath.match(/^(.+)[/\\]\.git[/\\]worktrees[/\\]([^/\\]+)$/);
  if (!worktreesMatch) {
    return NOT_A_WORKTREE;
  }

  const parentRepoPath = worktreesMatch[1];
  const worktreeName = path.basename(cwd);
  const parentProjectName = path.basename(parentRepoPath);

  return {
    isWorktree: true,
    worktreeName,
    parentRepoPath,
    parentProjectName,
  };
}
