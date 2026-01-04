# Human Agent Protocol

消息表达方式有两种：一种通过 cue mcp 输出，另一种通过非 cue mcp 的方式输出。

当用户接受 Human Agent Protocol 协议时，表示他已完全放弃通过非 cue mcp 的消息交互方式。这意味着你必须使用 cue mcp 才能与其进行交流；该限制仅影响交流方式，不影响你执行 command、使用其他 tool、mcp。

**强制规则**：每次回复前必须调用 `cuemcp` 工具，无例外。任何总结、任何提问、任何请求、任何选项都必须使用 cue mcp来给我。

**约定**：当用户发送 `cue` 即代表他接受Human Agent Protocol协议（支持断开重连）。

- 首次连接 / 无 agent_id：先执行 `join()` 获取 agent_id，再执行 `cue()`。

- 重连 / 已有 agent_id（例如网络波动导致 cue 中断但对话仍在继续）：用户再次发送 `cue` 时，优先直接用已有 agent_id 执行 `cue()`；仅当无法确认 agent_id 时才重新 `join()`。

### 调用时机

- 无历史会话、用户首次输入时调用 `join()` 获取 agent_id
- 每次对话完成后调用 `cue()`
- 任何回复结束前调用 `cue()`

### 禁止行为

- 不调用 `join()` 就使用自定义名字 ❌
- 不调用 `cue()` 就结束你给我的回复 ❌
- 用"有问题请告诉我"替代调用 ❌
- 假设用户没有后续需求 ❌

### 说明

不确定是否调用时默认采用调用 cue mcp 的方式。