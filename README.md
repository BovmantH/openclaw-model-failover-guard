# OpenClaw Model Failover Guard

Automatic model failover + failback guard for OpenClaw.

When your primary model becomes unstable, this guard can switch to an available fallback model automatically, then switch back to the primary after stability is restored.

---

## English

### What it does

- Monitors OpenClaw model health on an interval
- If primary fails N times consecutively → auto failover
- Selects fallback from **all configured models**
- Supports preferred fallback provider (e.g. `baishanyun`)
- After fallback is stable for N checks → attempts failback to primary
- If failback test fails → reverts to current fallback

### Key design goals

- **Generic/public-ready** (not hardcoded to one user's models)
- **Config-driven** behavior
- **Auditability** (state + logs)

### Files

- `SKILL.md` — skill definition and usage notes
- `config.example.json` — configurable defaults
- `scripts/failover.py` — runtime guard script

### Configuration

Copy `config.example.json` to `config.json` and edit:

- `primaryModel`: optional; empty = use OpenClaw current default
- `preferredFallbackProvider`: optional provider preference
- `excludedProviders`: providers to exclude from fallback candidates
- `failThreshold`, `recoverThreshold`
- `checkIntervalSec`, `testTimeoutSec`

### Run

```bash
python3 scripts/failover.py once
python3 scripts/failover.py loop
```

### State and logs

- State: `~/.openclaw/failover-state.json`
- Log: `~/.openclaw/failover.log`

---

## 中文

### 功能说明

- 按固定间隔检测 OpenClaw 当前模型健康
- 主模型连续失败 N 次后自动切换到兜底模型
- 兜底模型从**用户已配置的全部模型**中选择
- 支持优先 provider（如 `baishanyun`）
- 兜底稳定运行 N 次后尝试自动切回主模型
- 若切回测试失败，自动回退到当前兜底模型

### 设计目标

- **通用开源版**（不写死个人模型）
- **配置驱动**（阈值/优先级可调）
- **可审计**（状态文件 + 日志）

### 文件结构

- `SKILL.md`：技能定义与使用说明
- `config.example.json`：配置模板
- `scripts/failover.py`：守护脚本

### 配置方式

复制 `config.example.json` 为 `config.json` 后修改：

- `primaryModel`：可空；空则读取 OpenClaw 当前默认模型
- `preferredFallbackProvider`：优先兜底 provider
- `excludedProviders`：排除的 provider
- `failThreshold`、`recoverThreshold`
- `checkIntervalSec`、`testTimeoutSec`

### 运行方式

```bash
python3 scripts/failover.py once
python3 scripts/failover.py loop
```

### 状态与日志

- 状态：`~/.openclaw/failover-state.json`
- 日志：`~/.openclaw/failover.log`
