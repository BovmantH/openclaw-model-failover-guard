---
name: model-failover-guard
description: 自动模型故障切换守护（failover/failback）。当主模型连续失败时自动切换到可用兜底模型，稳定后自动尝试切回主模型。Use when OpenClaw model endpoints are unstable and you need service continuity with automatic rollback and audit logs.
---

# Model Failover Guard

给 OpenClaw 提供"主模型故障自动切换 + 恢复自动切回"。

详细文档请查看 [skills/model-failover-guard/SKILL.md](./skills/model-failover-guard/SKILL.md)

## 安装

```bash
npx skills add BovmantH/openclaw-model-failover-guard --skill model-failover-guard
```

## 功能

- 主模型连续失败自动切换到备用模型
- 备用模型稳定后自动切回主模型
- 支持 preferred fallback provider 优先级
- 完整的审计日志

## 配置

复制 `config.example.json` 为 `config.json` 并按需修改：

- `primaryModel`: 主模型（可空，默认使用 openclaw 当前主模型）
- `preferredFallbackProvider`: 首选备用 provider
- `failThreshold`: 故障切换阈值（默认 3）
- `recoverThreshold`: 切回阈值（默认 3）
- `checkIntervalSec`: 检查间隔（默认 300 秒）

## 文件

| 路径 | 用途 |
|------|------|
| `config.example.json` | 配置示例 |
| `guard.py` | 主守护脚本 |
| `models.py` | 模型健康检查与切换逻辑 |
| `audit_log.py` | 审计日志记录 |

## 关键词

openclaw skill, model failover, automatic failback, model routing, reliability, high availability
