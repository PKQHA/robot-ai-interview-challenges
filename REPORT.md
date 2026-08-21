# 完成报告

## 完成情况

已完成：

- 题目要求的 `Event`、`Effect` 和 `RobotApplication` 导入路径。
- 全部七种输入事件。
- 首次迎宾、重复迎宾抑制、对话/会议抑制、离场超时、短暂离开返回、完整离场后状态重置以及隔离的 snapshot。
- 覆盖全部必需场景和题目完整时间线的自动化测试。
- `PLAN.md`、`ARCHITECTURE.md`、`REPORT.md`、`AI_USAGE.md` 和 `requirements.txt`。

## 手工功能测试

离场 10 秒边界使用以下公共接口逐步验证：

```python
from robot_application.application import RobotApplication
from robot_application.models import Event

app = RobotApplication()

app.handle_event(Event("PERSON_ENTERED", 0))
app.handle_event(Event("PERSON_LEFT", 5))
app.handle_event(Event("TICK", 14.999))
app.handle_event(Event("TICK", 15))
```

逐步观察到的结果：

1. `PERSON_ENTERED`：返回 `wave_hand` 和“欢迎光临”。
2. `PERSON_LEFT`：返回 `[]`，刚离开时不立即送客。
3. `TICK, 14.999`：返回 `[]`，离开 9.999 秒时不送客。
4. `TICK, 15`：返回一次“感谢光临，欢迎下次再来”，正好离开 10 秒时确认送客。

## 自动化测试

按照题目要求，使用 pytest 覆盖全部必需场景：

```text
python -B -m pytest -q -p no:cacheprovider
```

测试结果：

```text
..........                                                               [100%]
10 passed
```

## 实现说明

题目也没有规定语音的 `effect_type` 或送客语原文。当前实现使用 `SPEECH` 和 `感谢光临，欢迎下次再来`，这两个选择均在测试和架构文档中明确说明。

## ROS 2 分析

### 已知事实

- 应用日志记录了一个 `effect_type=ROBOT_ACTION`、`value=wave_hand` 的效果已创建。
- `robot_bridge` 对 `task-17` 先记录了 `request_submitted`，随后记录了 `accepted_async`。
- 检查时，`/basic_action_play_v2` 有一个 action client，action server 数量为零。
- `/get_robot_mode` 返回 `mode_name: STAND`。
- 检查时，`robot-action.service` 状态为 `inactive`。

这些事实只能证明请求到达了应用到桥接层的提交路径，不能证明 ROS 2 action server 接受了目标、动作已经开始、动作执行成功或实体机器人已经运动。

### `accepted_async` 是否代表挥手完成

不代表。根据现有日志，它只能证明 `robot_bridge` 按该组件的日志语义接受了请求并进入异步提交流程。ROS 2 Action 分别具有目标接受、反馈和最终结果阶段。要证明动作完成，至少需要成功的终态结果；如果要声称真实机器人已经挥手，还需要相应的硬件层观察证据。

### 最可能出现问题的层级

**推断：**问题最可能位于 `robot_bridge` 下游的 ROS 2 action server 或进程启动层。观察到 action server 数量为零，说明当前没有服务端可以执行 `/basic_action_play_v2`；同时 `robot-action.service` 处于 `inactive`，这是一个较强的候选原因。

但目前还不能确认直接因果关系：该服务可能是有意停止、名称不一致、未通过 systemd 启动、运行在其他 ROS Domain 或命名空间，也可能在注册 action server 之前就已失败。

### 下一步检查顺序

1. 保持真实执行机构禁用，不要反复提交运动或动作目标。
2. 检查 `systemctl status robot-action.service` 和 `journalctl -u robot-action.service`，确认服务为何处于非活动状态。
3. 核对预期可执行文件、service unit 配置、环境变量、工作区 sourcing 和进程归属。
4. 核对 ROS 图身份信息：Action 名称和类型、命名空间、`ROS_DOMAIN_ID`、RMW 实现，以及预期节点是否存在。
5. 再次运行 `ros2 action info /basic_action_play_v2`；只有确认 action server 已存在，才继续发送目标。
6. 先在仿真、mock server 或执行机构禁用的环境中测试，并记录目标响应、反馈和最终结果。
7. 仅在获得安全许可并完成硬件检查后，进行有人监督的台架动作测试，并观察实体执行结果。

### 待验证项

- `robot_bridge` 源码中 `accepted_async` 的确切含义。
- `robot-action.service` 为何处于 `inactive`，以及它是否负责预期的 action server。
- Action 名称、类型、命名空间、ROS Domain 和已加载工作区是否一致。
- 是否有目标被排队、拒绝、超时或丢弃。
- 机器人安全联锁和硬件通信是否正常。

### 当前能否直接执行真实动作

不能。当前观察到的 ROS 图中没有 action server，可能负责服务端的系统服务处于非活动状态，没有 Action 最终结果，同时也没有验证硬件安全性和就绪状态。现有证据不足以证明真实动作能够安全或成功执行。

## 未完成项

无功能或文档未完成项。
