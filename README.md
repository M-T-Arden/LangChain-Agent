# Repo Intro

`first.py` is a practice exercise for LangChain quick start.
`log-agent` is a small SOC log analysis agent built with LangGraph and local tool calling.

# Mini SOC 日志分析 Agent
[English](#mini-soc-log-analyzer-agent)

这是一个基于 `log-agent/` 文件夹实现的轻量级 SOC 日志分析 Agent。它读取日志文件、提取可疑活动、缓存中间结果，并输出结构化 JSON 报告。

## 🎯 功能边界 (Scope & Boundaries)

为了保持架构轻量、安全与可控，本项目在设计上明确了以下边界：

1. **确定性工具集（无独立 Skills 层）**
   - 本项目不包含复杂的动态 Skills 自主生成层。
   - Agent 仅使用开发者显式定义的静态工具，LLM 通过 LangGraph 的工具调用机制决定是否触发这些工具。
2. **本地安全执行（无沙箱隔离）**
   - 本项目不依赖 Docker 或远端执行环境。
   - 所有日志读取与威胁情报检索都由本地 Python 函数执行，避免任意代码生成与执行风险。
3. **确定性输出**
   - 最终输出被约束为 JSON 格式报告，便于后续 SOC 自动化系统接入。

---

## 🏗️ 实现方式 (Architecture & Implementation)

`log-agent` 由三部分组成：

- `log-agent/main.py`: 构建 LangGraph 状态图并启动 Agent。
- `log-agent/graph.py`: 定义状态字典、LLM 调用节点、工具执行节点、意图解析节点与最终汇总节点。
- `log-agent/tools.py`: 定义可供 Agent 调用的本地工具函数和静态威胁情报数据。

### 核心工作流 (LangGraph Workflow)

Agent 的执行流程如下：

```text
[START] -> Node: llm_call
              |
              +---> (LLM 决定是否调用工具?)
                      |
                      +--- YES ---> Node: tool_node -> 回到 llm_call
                      |
                      +--- NO  ---> Node: summary_node -> END
```

当 LLM 生成工具调用意图时，`graph.py` 会通过 `intent_node` 解析工具名称和参数，随后 `tool_node` 执行对应工具，并将结果返回给模型继续分析。

---

## 🔧 `log-agent` 工具说明

当前 Agent 提供三个本地工具：

1. `parse_logs(log_path: str)`
   - 读取指定日志文件
   - 提取可疑活动事件
   - 将结果写入 `logs/cache/<log_name>_suspicious_activities.json`
   - 返回缓存文件路径提示
2. `find_threat_from_logs(CACHE_PATH: str)`
   - 从缓存文件读取可疑活动
   - 匹配本地静态威胁情报库 `THREAT_IPS`
   - 返回可疑 IP 的威胁评分与标签
3. `map_threats_to_mitre(CACHE_PATH: str)`
   - 从缓存文件读取事件类型
   - 将事件映射到 `MITRE_MAPPING` 中预定义的 ATT&CK 技术与战术

### 样例检测逻辑

`parse_logs` 会将以下条件视为可疑：

- `event` 为 `LOGIN_FAILED`, `MFA_FAILURE`, `UNAUTHORIZED_ACCESS`, `NETWORK_ALERT`
- `status` 为 `ERROR`, `CRITICAL`, `ALERT`, `TIMEOUT`, `THREAT_DETECTED`
- `user_agent` 中包含 `Wget`

它会将匹配事件提取为可疑活动列表并写入缓存。

---

## 🛠️ 快速开始

1. 激活 Python 虚拟环境。
2. 确保本地 Ollama 服务可用，并且 `log-agent/tools.py` 中的 `ChatOllama` 配置正确。
3. 运行：

```powershell
python log-agent/main.py
```

4. 默认示例日志路径为 `logs/sample.json`。
5. 运行结果会在终端中以节点级别输出，最终由 `summary_node` 生成 JSON 格式的汇总结果。

---

## 🧠 关键实现点

- `log-agent/graph.py` 中的 `llm_call` 使用 `model_with_tools.invoke(...)` 让模型决定是否调用工具。
- `intent_node` 负责将模型文本意图转换为结构化工具调用。
- `summary_node` 负责最终汇总，强制输出如下 JSON：

```json
{
  "summary": "<Overall log summary>",
  "potential_threats": "<List of threats found>"
}
```

- `log-agent/tools.py` 使用静态威胁情报字典 `THREAT_IPS` 和 MITRE 事件映射 `MITRE_MAPPING`，实现本地威胁分析与 ATT&CK 映射。

---

# Mini SOC Log Analyzer Agent

A lightweight SOC log analysis agent built on LangGraph.

## 🎯 Scope & Boundaries

This project deliberately maintains a small, deterministic architecture:

1. Deterministic toolset: the agent uses only explicit local tools defined in `log-agent/tools.py`.
2. Local execution: no sandbox or remote code execution is required.
3. Structured JSON output: the final result is constrained to a JSON report.

---

## 🏗️ Architecture & Implementation

The `log-agent` workflow is assembled in `log-agent/main.py` using `StateGraph`:

- `llm_call`: sends messages to the model and may return tool invocation requests.
- `tool_node`: executes actual tool calls from `tools.py`.
- `intent_node`: parses model output into a valid tool call.
- `summary_node`: generates the final JSON summary.

The state graph loops until the model stops calling tools, then outputs a clean, structured JSON report.

---

## 🔧 Available tools

- `parse_logs(log_path: str)`: parse a log file and cache suspicious activities.
- `find_threat_from_logs(CACHE_PATH: str)`: check suspicious IPs against local threat intelligence.
- `map_threats_to_mitre(CACHE_PATH: str)`: map suspicious events to MITRE ATT&CK techniques.

---

## 🛠️ Quick Start

Run:

```powershell
python log-agent/main.py
```

The default test log is `logs/sample.json`, and the agent prints node outputs during execution.
