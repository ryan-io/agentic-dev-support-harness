---
paths: ["**/Assets/**/*.cs"]
---

# Unity Code Standards

Extends `code-standards` and `csharp-code-standards`. Within this glob, the following supersede the general rules; everything not superseded still applies.

## Supersessions

- **DI**: constructor injection is impossible for engine-instantiated types (`MonoBehaviour`, `ScriptableObject`). Use VContainer injection via the `LifetimeScope` composition root. Never `new` a service; never service-locate.
- **Null checks**: for `UnityEngine.Object` subtypes use `==` / `!=`, not `is null` / `is not null` / `?.` / `??`. Unity overloads `==` to report destroyed objects as null; pattern matching bypasses that lifetime check. Non-Unity types keep the C# rule.
- **Async**: UniTask is the edge vocabulary, not `Task`. Do not use `ConfigureAwait(false)` in gameplay code (main-thread-bound). Cancellation flows from `MonoBehaviour.destroyCancellationToken`. `async UniTaskVoid` only for fire-and-forget entry points. Pure-tier code keeps TPL.
- **Nullable reference types**: not enabled in `Assets/`. NRT lives in the pure tier where fake null cannot mislead it.

## Humble Object

MonoBehaviours capture input, render output, forward lifecycle. Zero business logic; logic belongs in the pure-tier asmdefs behind Contracts ports. If a method does not need `UnityEngine`, it does not belong in this glob.

## Lifecycle

- `Update` for per-frame presentation; `FixedUpdate` for physics-rate work only.
- Cache component references in `Awake`/`OnEnable`; no `GetComponent` or `Find*` in per-frame paths.
- FEPM discipline: never rely on domain reload to reset statics. Avoid mutable statics; where one is unavoidable, manage it with the Editor Lifecycle attributes, not `[InitializeOnLoad]` + domain-unload events.

## Asset Discipline

- Every asset under `Assets/` pairs with a `.meta` file. Create, move, rename, and delete them together. Never hand-edit GUIDs.
- Never hand-edit `.unity`, `.prefab`, `.asset`, or `.meta` YAML. Scene and prefab changes go through the Editor (or the MCP bridge).

## Logging

Use the project logging port. `Debug.Log` only in adapters and editor-only code, never in anything the pure tier can reach.
