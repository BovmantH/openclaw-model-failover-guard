---
name: model-failover-guard
description: Automatic model failover daemon for OpenClaw. When the primary model fails consecutively, automatically switch to an available fallback model, and switch back after stability is restored. Use when OpenClaw model endpoints are unstable and you need service continuity with automatic rollback and audit logs.
---

# Model Failover Guard

Automatic model failover + failback guard for OpenClaw.


> This guard performs model failover and failback. It does **not** adapt request payloads across heterogeneous providers. Only pre-validated compatible fallback candidates should be used.

## How It Works

1. Read the current default primary model from `~/.openclaw/openclaw.json` (or use `config.json` to specify `primaryModel`)
2. When the primary model fails consecutively beyond the threshold, build a candidate pool (prefer `allowedFallbacks` if set, otherwise all configured models)
3. Skip excluded providers and cooldown candidates, then probe each candidate (if enabled)
4. Select the first healthy candidate, switch to it, and restart gateway
5. After the fallback runs stably beyond the threshold, attempt to switch back to the primary model
6. If failback fails, immediately revert to the fallback to avoid flapping

## Configuration

Copy `config.example.json` to `config.json` and modify as needed:

- `primaryModel`: Optional; if empty, automatically use OpenClaw's current default primary model
- `preferredFallbackProvider`: Optional; specify your preferred fallback provider
- `excludedProviders`: List of providers to exclude from fallback candidates
- `allowedFallbacks`: Optional; if set, only these models can be selected as fallbacks
- `candidateProbe`: Enable/disable probe and timeout (default enabled)
- `candidateCooldown`: Cooldown durations for candidates that fail probes
- `failoverOnErrors`: Error types that can trigger failover (default: http_429, http_5xx, timeout, connection)
- `failThreshold`: Failover threshold (default: 3)
- `recoverThreshold`: Failback threshold (default: 3)
- `checkIntervalSec`: Check interval (default: 300 seconds)
- `testTimeoutSec`: Primary/fallback test timeout (default: 45 seconds)

## Files

- Daemon script: `{baseDir}/scripts/failover.py`
- Example config: `{baseDir}/config.example.json`
- Runtime state: `~/.openclaw/failover-state.json`
- Logs: `~/.openclaw/failover.log`

## Usage

### One-time check (non-daemon)

\`\`\`bash
python3 {baseDir}/scripts/failover.py once
\`\`\`

### Run as daemon (foreground)

\`\`\`bash
python3 {baseDir}/scripts/failover.py loop
\`\`\`

### View logs

\`\`\`bash
tail -n 50 ~/.openclaw/failover.log
\`\`\`

## Safety

- Does not delete files
- Only modifies `agents.defaults.model.primary` and restarts gateway when conditions are met
- All switch actions are logged for audit purposes

---

# Model Failover Guard（中文）

给 OpenClaw 提供"主模型故障自动切换 + 恢复自动切回"。

## 通用逻辑

1. 从用户 \`~/.openclaw/openclaw.json\` 读取当前默认主模型（或使用 \`config.json\` 指定 \`primaryModel\`）
2. 主模型连续失败达到阈值后，先构建候选池（若设置了 `allowedFallbacks` 则只在其中选，否则使用全部配置模型）
3. 排除 excludedProviders 和冷却中的候选，然后按顺序探测（若启用 probe）
4. 选择首个健康候选并切换 + 重启 gateway
5. 在兜底稳定运行达到阈值后，尝试切回主模型
6. 切回失败则立即回退到兜底，避免抖动

## 配置文件

复制 \`config.example.json\` 为 \`config.json\` 并按需修改：

- \`primaryModel\`: 可空；空则自动使用 openclaw 当前默认主模型
- \`preferredFallbackProvider\`: 可空；可指定你偏好的 fallback provider
- \`excludedProviders\`: 不参与兜底的 provider 列表
- \`allowedFallbacks\`: 可选；设置后只允许这些模型参与兜底
- \`candidateProbe\`: 候选探测开关与超时（默认启用）
- \`candidateCooldown\`: 候选失败后的冷却时间配置
- \`failoverOnErrors\`: 允许触发 failover 的错误类型（默认 http_429, http_5xx, timeout, connection）
- \`failThreshold\`: 故障切换阈值（默认 3）
- \`recoverThreshold\`: 切回阈值（默认 3）
- \`checkIntervalSec\`: 检查间隔（默认 300 秒）
- \`testTimeoutSec\`: 探测/测试超时（默认 45 秒）

## 文件

- 守护脚本：\`{baseDir}/scripts/failover.py\`
- 示例配置：\`{baseDir}/config.example.json\`
- 运行状态：\`~/.openclaw/failover-state.json\`
- 日志：\`~/.openclaw/failover.log\`

## 常用操作

### 单次检查（不常驻）

\`\`\`bash
python3 {baseDir}/scripts/failover.py once
\`\`\`

### 常驻运行（前台）

\`\`\`bash
python3 {baseDir}/scripts/failover.py loop
\`\`\`

### 查看日志

\`\`\`bash
tail -n 50 ~/.openclaw/failover.log
\`\`\`

## 安全边界

- 不会删除文件
- 仅在触发条件满足时改 \`agents.defaults.model.primary\` 并重启 gateway
- 所有切换行为写日志，便于审计
