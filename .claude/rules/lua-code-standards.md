---
paths: ["**/*.lua"]
---


# Lua Code Standards

Extends `code-standards.instructions.md`. Draws from the [LuaRocks](https://github.com/luarocks/lua-style-guide) and [lua-users](http://lua-users.org/wiki/LuaStyleGuide) style guides.

## Language Version

Target Lua 5.1. WoW addons run on a restricted 5.1 runtime: no `goto`, integer subtype, or bitwise operators.

## Formatting

Indent with 3 spaces, no tabs. LF line endings. One statement per line, no semicolons. No hard line-length limit: if a statement is too long, split it into named subexpressions. Blank lines between function definitions. Indent tables and callback bodies relative to the line start, not the opening delimiter.

## Naming

`snake_case` for locals, parameters, and functions. `PascalCase` for class tables and constructors (acronyms capitalize first letter only: `XmlParser`). `UPPER_SNAKE_CASE` sparingly for constants. `_` for ignored variables. Do not use uppercase names starting with `_` (reserved by Lua). Prefix boolean functions with `is_` or `has_`. Names with larger scope should be more descriptive; one-letter names are fine in small loops.

## Nil and Truthiness

Check for `nil` before indexing uncertain tables. Use `or` for defaults (`local x = input or "default"`). Use the short form in conditionals (`if name then`) unless distinguishing `nil` from `false`. Do not design APIs that depend on that difference.

## Strings

Double quotes by default. Single quotes when the string contains double quotes. `string.format` for complex formatting. In loops, accumulate into a table and `table.concat`.

## Tables

Populate fields at construction. Trailing commas on all fields. Plain `key` for identifiers, `["key"]` for non-identifiers; do not mix. Dot notation for known properties, subscript for variable keys. Do not mix array and dictionary entries. `t[#t+1]` over `table.insert` for appending. `next(t) == nil` to test emptiness.

## Functions

Prefer `local function f()` over `local f = function()`. Never omit parentheses on calls (including single-string or single-table arguments in most cases). Validate early, return early.

## Modules

Return a single table. No globals. No `module()`. Require into a local named after the last path component; do not rename. Public functions use dot syntax, private functions use `local function`. No side effects on require. Stateful modules should use a factory.

```lua
local bar = {}

local function helper(x) return x * 2 end

function bar.greet(name)
   return "Hello, " .. name
end

return bar
```

## OOP

Class metatable is local with `__index = self`. Colon syntax for method definitions and calls. Constructor exported on the module table. Do not rely on `__gc` for non-memory resources; provide `close`.

## Error Handling

Expected failures return `nil, error_message`. API misuse throws via `error()` or `assert()`. Use `pcall`/`xpcall` at boundaries only. Never suppress errors silently.

## Type Checking

In non-hot-path code, assert argument types at public boundaries: `assert(type(x) == "string")`. Use `tostring`/`tonumber` explicitly; do not rely on coercion.

## Scope and Performance

Always `local`. Narrowest scope possible; use `do`/`end` blocks when helpful. Localize hot globals (`local pairs = pairs`). Avoid allocations (closures, tables) inside tight loops.

## Static Analysis

Code should pass luacheck. Provide `.luacheckrc` for exceptions. Whitespace warnings (6xx) and intentional unused-variable warnings (211-213) may be suppressed.

## WoW Addon Conventions

Use the namespace table from the loader (`local addonName, ns = ...`). Register events through a single frame or AceEvent. No frame creation on every event fire. `C_Timer.After`/`C_Timer.NewTicker` over OnUpdate for timed work.

## Testing

Use busted. Tests in `spec/`. File names mirror the module with `_spec` suffix. Follow Arrange-Act-Assert and `Method_State_ExpectedBehavior` naming per `testing.instructions.md`.
