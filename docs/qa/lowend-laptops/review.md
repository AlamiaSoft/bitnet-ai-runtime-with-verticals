Good. **79/79 is solid**, and the low-end path is now substantially better.

Only a few things I'd still flag:

| Area                                 | Verdict | Remaining concern                                                                                        |
| ------------------------------------ | ------- | -------------------------------------------------------------------------------------------------------- |
| Native CPU runtime                   | ✅       | Correctly preferred when capable                                                                         |
| AVX2 detection                       | ✅       | Good defensive check                                                                                     |
| Threading                            | ✅       | Better low-end behavior                                                                                  |
| Docker dependency                    | ✅       | No longer a prerequisite                                                                                 |
| Remote fallback                      | ✅       | Good escape hatch                                                                                        |
| Tests                                | ✅ 79/79 | Strong regression coverage                                                                               |
| **AVX2-only assumption**             | ⚠️      | Native runtime is still tied to AVX2; eventually support other CPU builds/features                       |
| **Automatic model download**         | ⚠️      | ~1.2 GB download can be painful on low-end/slow connections; make it explicit/progress-aware             |
| **Memory/resource detection**        | ⚠️      | Add RAM-based model/runtime eligibility, not just CPU instruction detection                              |
| **Runtime startup lifecycle**        | ⚠️      | Alamia should start/stop/manage the native runtime automatically rather than making users run PowerShell |
| **Actual no-Docker acceptance test** | 🔴      | Make sure there is a CI/manual test with Docker unavailable, not merely mocked resolver behavior         |

### The biggest remaining product issue

The final UX should **not expose `start-portable.ps1` to ordinary users**.

Ideally:

```text
Alamia starts
   ↓
Hardware detection
   ↓
Native BitNet available?
   ↓
Start native runtime automatically
   ↓
127.0.0.1:8080
```

The PowerShell launcher should become an **internal runtime bootstrapper**, not part of the user's mental model.

Also, don't over-optimize the 2–3 second BitNet response yet. **Correct routing + zero Docker dependency matters more right now.**

I'd call the **routing architecture + low-end runtime milestone essentially complete** once you have that genuine Docker-disabled end-to-end test.




2 things to add to above instructions for the dev agent:

1. instead of always running one runtime type perhaps the system should allow the user to select runtime: Native Windows Vs Docker (if both are available); or better prompt the user about available resources and let them choose and set as a preference for future runs
2. why AVX2 assumption?? can we not make native runtime cpu build/architecture agnsotic??

Yes. Add both, but I would sharpen the requirements:

### 1. Runtime selection should be a **user preference + automatic recommendation**

Don't force `Native Windows` or `Docker`.

At startup, detect:

* Native runtime available
* Docker available
* CPU architecture/instruction sets
* RAM
* GPU/VRAM
* available disk
* model availability
* estimated suitability/performance

Then show something like:

> **Recommended: Native CPU** — lowest overhead, no Docker required
> Docker Runtime — available, isolated, slightly higher overhead
>
> **[Use Recommended] [Choose Runtime]**

Save the choice as a preference:

```text
runtime_preference = auto | native | docker
```

**`auto` should be the default.**

If the user's selected runtime becomes unavailable, don't silently switch permanently. Fall back according to policy and tell them:

> Native runtime unavailable → using Docker fallback.

Also allow **"Remember my choice"**.

### 2. Yes — don't architect around AVX2

The current AVX2 requirement is an artifact of the **specific precompiled binary**, not a fundamental Alamia requirement.

The correct architecture is:

```text
Alamia
  ↓
CPU architecture detection
  ↓
Instruction-set detection
  ↓
Select compatible native runtime binary
```

For Windows x64, ideally have runtime builds along the lines of:

```text
generic/x64
AVX2
AVX-512
ARM64
```

and select the highest compatible build.

Even better, use **runtime dispatch** where the underlying inference engine supports it, rather than maintaining unnecessary separate builds.

For unsupported hardware:

```text
Native optimized build unavailable
        ↓
compatible native build?
        ↓
yes → use it
no  → Docker / remote / another model
```

So **do not make `has_avx2()` a prerequisite for "native CPU" itself**. Make it one capability used to select the appropriate native binary.

### Instruction I'd give the agent

> Refactor runtime selection to support `auto | native | docker` user preferences, with automatic hardware/resource assessment and a recommended runtime on first launch. Docker must remain optional. Persist the user's preference and expose it in settings.
>
> Remove AVX2 as a hard architectural requirement. Treat CPU instruction sets as runtime capabilities used to select the best compatible native binary/build. Design native runtime discovery around CPU architecture + supported instruction sets, with graceful fallback to a compatible build, Docker, another local runtime, or remote execution. Alamia itself must not require AVX2.
