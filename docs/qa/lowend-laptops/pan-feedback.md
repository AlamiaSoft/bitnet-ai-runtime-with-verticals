The plan is **good**, but I'd make 4 corrections before approving it:

| Item               | Decision                                                                                                                                                                                                                           |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Q1 Generic x64** | **Do not automatically use it on very weak CPUs.** Native compatibility ≠ usable performance. Hardware assessment should estimate suitability; if generic is predicted unusably slow, recommend Docker/remote/another small model. |
| **Q2 ARM64**       | **Defer actual ARM64 binary distribution**, but keep the architecture abstraction. Don't ship a fake placeholder.                                                                                                                  |
| **Q3 psutil**      | **Add `psutil`**. This is a small, mature dependency and makes RAM/resource detection much cleaner cross-platform.                                                                                                                 |
| **Q4 UI**          | **Yes, dashboard UI now.** This is a user-facing runtime choice, not merely an API feature. Show recommendation + available runtimes + persistent preference.                                                                      |

### One important correction to their binary-selection design

This:

```text
performance_rank:
avx512 = 3
avx2 = 2
generic = 1
```

is too simplistic.

**Instruction-set support and actual suitability are different things.**

The resolver should produce something like:

```text
Hardware
├── x86_64
├── AVX2 ✓
├── 8 GB RAM
├── GPU ✗
└── Native BitNet AVX2 ✓

Available runtimes
├── Native AVX2      → excellent
├── Native generic   → unnecessary
└── Docker           → available

Recommendation
→ Native AVX2
```

On an ancient CPU:

```text
x86_64
AVX2 ✗
generic ✓
RAM 4 GB

Native generic → compatible but poor performance
Docker → available
Remote → available

Recommendation
→ Remote / lightweight model
```

### Also change this preference behavior

I would **not** make:

`NATIVE → native → remote`

without considering Docker.

If the user explicitly chooses **Native**, that's fine: honor it.

But if native becomes unavailable, clearly report:

> Native runtime unavailable. Choose Docker or enable Auto.

Don't silently violate a deliberate user preference.

For `AUTO`, however:

```text
discover capabilities
        ↓
recommend best runtime
        ↓
native / docker / remote
```

### And one conceptual improvement

`runtime_preference = auto | native | docker` is good, but eventually you probably want:

```text
auto
native
docker
remote
```

**Don't implement `remote` necessarily now**—just keep the abstraction open.

### Approval verdict

**Approve with these adjustments.**

Most importantly, tell the agent:

> **Do not equate "binary exists and CPU can execute it" with "this is the best runtime." Runtime selection must consider compatibility + performance + RAM + user preference.**

That distinction will prevent another routing mess six months from now.
