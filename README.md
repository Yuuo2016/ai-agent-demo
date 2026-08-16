# AI Agent 实战题 · 题三 热点发现 Agent

面试实战题实现：**题三 热点发现 Agent**（Hot Topic Discovery Agent）。

> 题二（内容运营 Agent）已独立迁移至仓库 `Yuuo2016/ai-content-agent`。

## 请使用本仓库代码。

## 功能亮点

- 多源聚合：RSS（36氪 / 机器之心 / Hacker News / Reddit）+ GitHub Trending
- AI 筛选 + 中文摘要 + 价值评分(0-10) + 入选理由
- **合并同一事件**：基于关键词 Jaccard 相似度，把同一热点的多篇报道聚为一条
- **评估可信度**：可量化公式 `来源权威 × 交叉印证 × 时效`，并展示评分依据
- **总结不同观点**：AI 对同一事件列出不同来源/立场的观点
- **多渠道推送**：飞书 + SMTP 邮件 + 企业微信（按配置自动启用）
- 逐条人工审核（`e`编辑 / `r`拒绝 / `p`完成推送），`e`/`r` 不推送

## 项目结构

```
ai-agent-demo/
├── common/                  # 公共模块
│   ├── llm.py               # LLM 封装（OpenAI 兼容接口）
│   ├── feishu.py            # 飞书 webhook 推送
│   ├── push.py              # 多渠道推送（飞书/邮件/企业微信）
│   └── human_review.py      # 人工审核节点（风险控制，通用）
├── problem3_hotspot/        # 题三：热点发现 Agent
│   ├── main.py              # 主流程
│   ├── sources.py           # 数据源（RSS/GitHub/Reddit）
│   ├── event_cluster.py     # 事件聚类 + 可信度评估
│   └── review_items.py      # 逐条人工审核 + 多渠道推送
├── docs/                    # 演示文档
├── output/                  # 输出目录（报告）
├── requirements.txt
└── .env.example             # 配置模板
```

## 快速开始

### 1. 安装依赖

```bash
cd ai-agent-demo
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 LLM API Key 和至少一个推送渠道
```

### 3. 运行

```bash
python problem3_hotspot/main.py
```

## 配置说明

### LLM（OpenAI 兼容接口）

| 变量 | 说明 |
|:---|:---|
| `LLM_API_KEY` | 你的 API Key（必填） |
| `LLM_BASE_URL` | 服务商接口地址 |
| `LLM_MODEL` | 模型名 |

### 推送渠道（至少配置一个即可；不填自动跳过）

| 变量 | 说明 |
|:---|:---|
| `FEISHU_WEBHOOK` | 飞书自定义机器人 Webhook |
| `FEISHU_SECRET` | 飞书签名密钥（开启校验才填） |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USER` / `EMAIL_PASS` / `EMAIL_TO` | SMTP 邮件 |
| `WECOM_WEBHOOK` | 企业微信群机器人 Webhook |

## 工作流说明

```
监控数据源(RSS/GitHub/Reddit) → 合并同一事件(聚类)
    → AI筛选+摘要+价值判断+可信度评估+观点总结
    → 逐条人工审核(e/r/p) → 多渠道推送 + 本地报告
```

### 可信度评分公式（可量化、可解释）

```
可信度 = 来源权威分 × 交叉印证系数 × 时效系数
```

- 来源权威分：官方机构 0.95 / 权威媒体 0.85 / 科技媒体 0.75 / 社区 0.55 / 个人 0.45
- 交叉印证：同一事件被 N 家独立来源报道 → `1 + 0.1×(N-1)`，封顶 1.3
- 时效：当天报道 1.0，每天递减 0.05，最低 0.7

## 风险控制

- 推送前有人工逐条审核节点（`e`/`r` 不推送，`p` 才统一多渠道推送）
- 每条标注来源、可信度、合并来源数，可追溯
- 单源抓取失败不影响其余源；LLM 失败有原始数据兜底；推送失败不影响本地报告

## 当前局限

- 数据源抓取依赖网络，部分 RSS 源可能失效（代码已做容错）
- AI 生成内容需人工把关质量，避免事实性错误
- 飞书 webhook 有频率限制，演示时避免高频推送
