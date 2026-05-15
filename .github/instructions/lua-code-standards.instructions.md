---
applyTo: "**/*.lua"
---

# Lua Code Standards

These standards extend `code-standards.instructions.md` with Lua-specific rules. Both files apply when writing or reviewing Lua code.

## Language Version

Target Lua 5.1 unless the project explicitly requires a later version. WoW addons run on Lua 5.1 with a restricted standard library; do not use features from later versions (e.g., `goto`, integers, bitwise operators) in addon code.

## Nil Safety

Check for `nil` before indexing tables or calling methods on values that may not exist. Use `or` for defaults (`local name = input or "unknown"`). Avoid long chains of unchecked table access; extract into a local with a guard.

## Naming

Use `snake_case` for local variables and functions. Use `PascalCase` for module-level tables, classes, and constructors. Use `UPPER_SNAKE_CASE` for constants. Prefix private/internal functions with an underscore when exposing a module table.

## Tables

Tables are the only data structure. Use them deliberately: distinguish between arrays (sequential integer keys) and dictionaries (string or mixed keys). Do not mix array and dictionary entries in the same table. Use `#tbl` for array length only on pure sequences.

## Modules

Return a single table from each module file. Do not pollute the global namespace. Declare locals with `local` at the narrowest scope possible. Use `local function` for functions that do not need to be in the module table.

```lua
local M = {}

function M.greet(name)
    return "Hello, " .. name
end

return M
```

## Error Handling

Use `pcall` or `xpcall` at boundaries where errors are expected (loading user data, parsing external input). Inside trusted internal code, let errors propagate naturally. Provide meaningful error messages in `error()` calls. Do not use `pcall` to suppress errors silently.

## String Handling

Use `..` for concatenation. For heavy concatenation in loops, accumulate into a table and join with `table.concat`. Use `string.format` for complex formatting rather than chained concatenation.

## Performance

Localize frequently accessed globals (`local pairs = pairs`, `local math_floor = math.floor`) in hot paths. Avoid creating closures or tables inside tight loops. Prefer `ipairs` for sequential iteration and `pairs` for dictionary iteration.

## WoW Addon Conventions

When writing WoW addon code: use the addon's namespace table passed to the file by the loader (`local addonName, ns = ...`). Register events through a single frame or use a library like AceEvent. Do not create frames on every event fire. Use `C_Timer.After` or `C_Timer.NewTicker` instead of OnUpdate for timed operations.

## Testing

Use busted as the test framework. Test files go in a `tests/` or `spec/` directory. Test file names mirror the module under test with a `_spec` suffix: `utils_spec.lua` for `utils.lua`. Follow Arrange-Act-Assert structure as defined in `testing.instructions.md`.
