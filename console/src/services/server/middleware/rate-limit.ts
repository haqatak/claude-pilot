/**
 * Rate Limiting Middleware for Remote Worker
 *
 * Simple in-memory rate limiter using sliding window algorithm.
 * Only applies to remote (non-localhost) requests.
 */

import type { Request, Response, NextFunction } from "express";
import { logger } from "../../../utils/logger.js";

/**
 * Rate limit entry for tracking requests
 */
interface RateLimitEntry {
  /** Timestamps of requests in the current window */
  timestamps: number[];
}

/** In-memory store for rate limiting */
const rateLimitStore = new Map<string, RateLimitEntry>();

/**
 * Check if request is from localhost
 */
function isLocalRequest(req: Request): boolean {
  const clientIp = req.ip || req.socket.remoteAddress || "";
  return clientIp === "127.0.0.1" || clientIp === "::1" || clientIp === "::ffff:127.0.0.1";
}

/**
 * Get rate limit key for request (uses token prefix or IP)
 */
function getRateLimitKey(req: Request): string {
  const token = req.headers.authorization?.slice(7, 23);
  if (token) {
    return `token:${token}`;
  }
  return `ip:${req.ip || req.socket.remoteAddress || "unknown"}`;
}

/**
 * Rate limiting middleware factory
 * @param maxRequests Maximum requests per window (default: 1000)
 * @param windowMs Window duration in milliseconds (default: 60000 = 1 minute)
 */
export function rateLimitMiddleware(maxRequests = 1000, windowMs = 60000) {
  return (req: Request, res: Response, next: NextFunction): void => {
    if (isLocalRequest(req)) {
      return next();
    }

    const key = getRateLimitKey(req);
    const now = Date.now();
    const cutoff = now - windowMs;

    let entry = rateLimitStore.get(key);
    if (!entry) {
      entry = { timestamps: [] };
      rateLimitStore.set(key, entry);
    }

    entry.timestamps = entry.timestamps.filter((ts) => ts > cutoff);

    if (entry.timestamps.length >= maxRequests) {
      const retryAfter = Math.ceil(windowMs / 1000);

      logger.warn("SECURITY", "Rate limit exceeded", {
        key,
        requests: entry.timestamps.length,
        limit: maxRequests,
      });

      res.setHeader("Retry-After", retryAfter.toString());
      res.setHeader("X-RateLimit-Limit", maxRequests.toString());
      res.setHeader("X-RateLimit-Remaining", "0");
      res.setHeader("X-RateLimit-Reset", Math.ceil((now + windowMs) / 1000).toString());

      res.status(429).json({
        code: "RATE_LIMITED",
        message: "Too many requests",
        retryAfter,
      });
      return;
    }

    entry.timestamps.push(now);

    const remaining = maxRequests - entry.timestamps.length;
    res.setHeader("X-RateLimit-Limit", maxRequests.toString());
    res.setHeader("X-RateLimit-Remaining", remaining.toString());
    res.setHeader("X-RateLimit-Reset", Math.ceil((now + windowMs) / 1000).toString());

    next();
  };
}

/**
 * Clear rate limit store (for testing)
 */
export function clearRateLimitStore(): void {
  rateLimitStore.clear();
}
