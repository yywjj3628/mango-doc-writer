# Mango Doc Writer — VPS 部署文件

## 文件说明

| 文件 | 作用 |
|------|------|
| `env.example` | 环境变量模板（复制为 .env 后填入真实值） |
| `check_env.py` | 部署前环境检查 |
| `healthcheck.py` | 运行时健康检查（轻量，不跑完整回归） |
| `run_single.sh` | 运行单篇输入或单个 case |
| `run_regression.sh` | 全量 10 case 回归测试 |
| `logrotate.example` | 日志轮转配置 |
| `systemd/` | systemd 定时回归（可选） |

## 快速开始

```bash
# 1. 配置环境
cp deploy/env.example .env
vim .env  # 填入 DEEPSEEK_API_KEY

# 2. 检查环境
python deploy/check_env.py

# 3. 健康检查
python deploy/healthcheck.py

# 4. 运行单 case
bash deploy/run_single.sh tests/cases/002-fake-report-real-request.md

# 5. 全量回归
bash deploy/run_regression.sh
```

## 注意事项

- `.env` 不得提交 Git（已在 .gitignore 中）
- API key 不得写入日志、报告、README
- 日志保留 30 天，debug 文件保留 7 天
- outputs/ 按需手动清理
