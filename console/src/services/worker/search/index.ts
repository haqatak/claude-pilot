/**
 * Search Module - Named exports for search functionality
 *
 * This is the public API for the search module.
 */

export { SearchOrchestrator } from "./SearchOrchestrator.js";

export { ResultFormatter } from "./ResultFormatter.js";
export { TimelineBuilder } from "./TimelineBuilder.js";
export type { TimelineItem, TimelineData } from "./TimelineBuilder.js";

export type { SearchStrategy } from "./strategies/SearchStrategy.js";
export { BaseSearchStrategy } from "./strategies/SearchStrategy.js";
export { VectorSearchStrategy, ChromaSearchStrategy } from "./strategies/VectorSearchStrategy.js";
export { SQLiteSearchStrategy } from "./strategies/SQLiteSearchStrategy.js";
export { HybridSearchStrategy } from "./strategies/HybridSearchStrategy.js";

export * from "./filters/DateFilter.js";
export * from "./filters/ProjectFilter.js";
export * from "./filters/TypeFilter.js";

export * from "./types.js";
