## LSP Servers - Code Intelligence

**Use LSP tools BEFORE grep/search for code understanding. LSP provides compiler-accurate results that grep cannot match.**

**Available:** Python (basedpyright), TypeScript (typescript-language-server), Go (gopls)

LSP servers are installed via plugins. No manual configuration needed.

### When to Use LSP

| Situation | LSP Operation | Why NOT grep |
|-----------|---------------|--------------|
| Finding unused functions | `findReferences` | Grep misses dynamic calls |
| Checking who calls a function | `findReferences` or `incomingCalls` | Grep finds text matches, not actual calls |
| Understanding function signature | `hover` | Grep can't infer types |
| Listing all functions in file | `documentSymbol` | More accurate than regex patterns |
| Before deleting/renaming | `findReferences` | Ensures you don't break callers |
| Tracing call chains | `incomingCalls`/`outgoingCalls` | Grep cannot follow call graphs |

### Operations

| Operation | Use Case | Python | TS | Go |
|-----------|----------|--------|----|----|
| `goToDefinition` | Find where symbol is defined | ✅ | ✅ | ✅ |
| `findReferences` | Find all usages of a symbol | ✅ | ✅ | ✅ |
| `hover` | Get type info and documentation | ✅ | ✅ | ✅ |
| `documentSymbol` | List all symbols in a file | ✅ | ✅ | ✅ |
| `workspaceSymbol` | Search symbols across codebase | ❌ | ✅ | ✅ |
| `incomingCalls` | Find callers of a function | ✅ | ✅ | ✅ |
| `outgoingCalls` | Find functions called by a function | ✅ | ✅ | ✅ |

### Parameters

All operations require: `filePath`, `line` (1-based), `character` (1-based)

### Examples

```
# List all symbols in a file
LSP(documentSymbol, "installer/cli.py", 1, 1)

# Get function signature and docs
LSP(hover, "installer/cli.py", 35, 5)

# Find where a symbol is defined
LSP(goToDefinition, "installer/cli.py", 14, 45)

# Find all usages before renaming
LSP(findReferences, "installer/cli.py", 35, 5)

# Find who calls this function
LSP(incomingCalls, "installer/cli.py", 35, 5)

# Find what this function calls
LSP(outgoingCalls, "installer/cli.py", 35, 5)
```

### When Grep is OK

Use grep/Glob when:
- Searching for string literals or comments
- Finding files by name pattern
- Looking for TODO/FIXME markers
- Searching across non-code files (markdown, config)

**For code understanding: LSP first, grep as fallback.**
