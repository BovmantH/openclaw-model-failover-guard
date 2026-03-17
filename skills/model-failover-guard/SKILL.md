---
name: model-failover-guard
description: Automatic model failover daemon for OpenClaw. When the primary model fails consecutively, automatically switch to an available fallback model, and switch back after stability is restored. Use when OpenClaw model endpoints are unstable and you need service continuity with automatic rollback and audit logs.
---

# Model Failover Guard

Automatic model failover + failback guard for OpenClaw.

## How It Works

1. Read the current default primary model from `~/.openclaw/openclaw.json` (or use `config.json` to specify `primaryModel`)
2. When the primary model fails consecutively beyond the threshold, select an available fallback from all configured models
3. Fallback candidates are prioritized by `preferredFallbackProvider`, then alphabetically
4. After the fallback runs stably beyond the threshold, attempt to switch back to the primary model
5. If failback fails, immediately revert to the fallback to avoid flapping

## Configuration

Copy `config.example.json` to `config.json` and modify as needed:

- `primaryModel`: Optional; if empty, automatically use OpenClaw's current default primary model
- `preferredFallbackProvider`: Optional; specify your preferred fallback provider
- `excludedProviders`: List of providers to exclude from fallback candidates
- `failThreshold`: Failover threshold (default: 3)
- `recoverThreshold`: Failback threshold (default: 3)
- `checkIntervalSec`: Check interval (default: 300 seconds)

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
2. 主模型连续失败达到阈值后，从"所有已配置模型"里选择可用兜底
3. 兜底候选按 \`preferredFallbackProvider\` 优先，其余模型按字典序
4. 在兜底稳定运行达到阈值后，尝试切回主模型
5. 切回失败则立即回退到兜底，避免抖动

## 配置文件

复制 \`config.example.json\` 为 \`config.json\` 并按需修改：

- \`primaryModel\`: 可空；空则自动使用 openclaw 当前默认主模型
- \`preferredFallbackProvider\`: 可空；可指定你偏好的 fallback provider
- \`excludedProviders\`: 不参与兜底的 provider 列表
- \`failThreshold\`: 故障切换阈值（默认 3）
- \`recoverThreshold\`: 切回阈值（默认 3）
- \`checkIntervalSec\`: 检查间隔（默认 300 秒）

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
