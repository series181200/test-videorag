# 视频内容查询测试 VQ

本目录负责模块二 AI 融合实践中的 Video Query（视频内容查询）业务链路，覆盖 `TC-VQ-001` 至 `TC-VQ-004`。重点验证查询准入、模型超时后恢复和同会话连续提问时的任务隔离。

已实现 4 个业务用例、22 个自动化检查：pytest 12 个、Vitest 10 个。两种框架在独立进程中执行，按同一业务 ID 汇总。业务源码未修改，失败断言和被前置问题阻断的检查均保留。

在仓库根目录一键运行：

```powershell
python Vimo-desktop/test_video_query/run_tests.py
```

也可执行 `npm.cmd test --prefix Vimo-desktop/test_video_query`。运行器先执行 pytest，即使失败也会继续执行 Vitest。依赖缺失时安装：

```powershell
python -m pip install -r Vimo-desktop/test_video_query/requirements-test.txt
npm.cmd install --prefix Vimo-desktop/test_video_query
```

本次使用已安装的 Python 依赖及 `test_renderer/node_modules`，没有安装包或修改其他目录锁文件。Vitest 固定为 2.1.9；React、React DOM、React Router、Testing Library 必须来自同一依赖目录，避免出现两个 React 实例导致 Invalid Hook Call。

每次运行保存到独立的 `results/<UTC时间戳>-<进程号>/`：包含原始 pytest XML、Vitest JSON、两份控制台日志、源码和测试哈希、命令及环境记录、业务汇总 JSON/CSV 和合并 JUnit XML。退出码 0 表示全部通过，1 表示有失败或未完成检查，2 表示依赖、收集或运行异常。

## 范围与框架约定

- 唯一业务分类标准是 VQ；不再按前端、IPC、API、算法四层组织业务用例。
- 测试 TypeScript / TSX 使用 **Vitest**；测试 Python 使用 **pytest**。
- 同一业务 ID 可以由两种框架分别验证。例如 pytest 检查进程与状态，Vitest 检查等待结束与结果展示；只通过其中一部分不代表整条业务链路通过。
- 负责查询本身的失败恢复；删除会话、损坏状态文件、进程无故消失等独立 SR 场景不在本目录扩展。
- 不评估大模型回答准确率，不调用真实付费模型，不使用 GPU。查询算法作为外部依赖替换，但查询准入、进程登记、状态写入和前端处理使用真实业务代码。

## 用例与实现思路

### TC-VQ-001 空白查询不能创建进程

**目标：** 空字符串、全空格、换行、制表符组成的问题被拒绝，不产生查询任务副作用。

- 入口：`python_backend/videorag_api.py` 的 `POST /api/sessions/<chat_id>/query`，必要时补充真实 `VideoRAGProcessManager` 调度检查。
- 主框架：pytest；前端补充检查使用 Vitest。
- 使用已存在且索引完成的会话，确保失败原因只来自查询输入。
- 参数集：`""`、`"   "`、`"\n"`、`"\t"`、`" \n\t "`；每个参数记录独立执行结果，业务统计仍为本 ID。
- 预期建议为 HTTP 400、`success: false`，且 `start_query_processing` 未调用、不创建进程、不新增 processing 状态。
- 增加 `"  视频讲了什么？  "` 正向对照，预期只启动一次，并传递 trim 后的问题，防止“全部拒绝”也通过。
- HTTP 400 是本测试方案的明确接口验收约定。阶段一的数字类型非法 query 不作为本阶段的主要新增内容。
- 当前路由对 query 执行 `.strip()` 后直接交给进程管理器，需要验证空白输入是否被阻止。

### TC-VQ-002 会话不存在或索引未就绪时不能启动查询

**目标：** 会话存在且索引完成才允许查询；请求不能绕过界面限制直接启动无效任务。

- 入口：查询路由、真实 `VideoRAGProcessManager.start_query_processing` 及会话索引状态读取。
- 框架：pytest；界面阻止提交的补充检查使用 Vitest。
- 构造三个独立状态：会话目录不存在；会话存在但无已完成索引；`indexing_status.status = processing`。
- 每个状态直接请求后端，检查拒绝结果、`multiprocessing.Process` 未创建/启动，以及没有写入新的查询 processing 状态。
- 对不存在会话，额外检查请求没有为了读取状态而创建出一个新的会话目录。
- 本次采用的接口验收约定：不存在返回 404；存在但未就绪返回 409；索引完成的对照用例可正常启动。404/409 是测试目标，不代表当前源码行为。
- 准入测试保留实际路由和管理器，不将管理器整体替换为“永远拒绝”的 Mock，否则无法验证准入逻辑。
- 使用 `tmp_path` 准备会话状态，替换 Process 等外部依赖，不真正创建模型工作进程。

### TC-VQ-003 模型超时后释放资源清除旧结果并支持成功重试

**目标：** 查询超时后有可读错误，本次任务结束且允许再次提问，旧结果不会成为重试问题的答案。

- Python 入口：`query_worker_process`、进程管理器、查询状态写入/读取。
- TypeScript 入口：`src/renderer/src/hooks/useChat.ts` 中的查询发起、轮询、`handleQueryError` 和结果处理。
- 框架：pytest 验证 worker、状态和任务生命周期；Vitest + jsdom 验证真实 hook/组件消费错误后的业务表现。
- 在索引完成的会话中准备旧查询结果，启动新查询；令模型依赖抛出明确的超时异常，而不是让测试真的等待模型超时。
- 检查终态是 error、本次活动结果不再包含旧答案、查询进程不再存活；管理器应移除活动登记或明确将其标为不可运行，不能将失效任务视为仍在执行。
- Vitest 按 processing → error 提供状态响应，检查结束轮询、解除回答中状态、显示错误并恢复提问入口。
- 恢复模型替身后提交新的问题，按 processing → completed 返回新答案，检查最终显示的是新问题的答案。
- “清除旧结果”指活动查询的状态/占位结果，不删除用户此前合法的历史对话。
- 仅 Mock 模型抛异常并断言调用了错误更新函数，不足以完成本项；应实际读回状态，另验资源管理和前端恢复。
- 模型主动抛超时与模型永不返回是不同问题。本项先实现主动超时恢复；若声明支持硬超时终止，必须另外验证超时执行机制，不能以抛异常替代证明。
- 当前 worker 的错误更新不包含 `answer` 清空，需结合查询启动时的清空及实际状态合并一起判断，不能只看错误分支就宣称旧答案残留。
- 阶段一已有“模型异常进入 error”检查；本项的增量是资源释放、真实持久化、旧结果隔离和成功重试。

### TC-VQ-004 问题 A 未完成时提交 B 不得覆盖任务和答案

**目标：** 同会话的并发查询行为明确，任务与答案不会互相覆盖。

- Python 入口：查询路由、`start_query_processing`、`running_processes`。
- TypeScript 入口：真实查询提交和答案展示逻辑。
- 框架：pytest + Vitest。
- 本次采用“同会话只允许一个活动查询，A 完成前拒绝 B”，接口返回 409 作为验收约定。若团队以后选择排队或并行，需先整体改写预期，不能运行后任选一个结果算通过。
- 使用两个可控的假进程对象，A 启动后保持存活，然后绕过 UI 再向后端提交 B。
- 检查 B 被拒绝、不启动第二个进程；A 的登记对象及 query 状态不被 B 覆盖，A 仍可完成并返回其自己的答案。
- A 完成后再次提交 B，应允许启动并显示 B 的答案；两个问题和结果应保持正确对应。
- Vitest 验证重复提交不能产生错位的消息或答案；只证明 UI 按钮被禁用，不代表后端并发保护已经通过。
- 当前后端使用 `f'{chat_id}_query'` 作为进程登记键，需验证重复启动是否覆盖原记录；不能通过 Mock 字典写入或整个管理器来掩盖问题。

## 已实现文件

当前目录结构：

```text
test_video_query/
  README.md
  run_tests.py              # 两种框架的运行、证据保存和业务汇总
  package.json
  requirements-test.txt
  pytest.ini
  conftest.py
  python_support.py         # 前置失败标记与公共断言
  test_query_validation.py   # TC-VQ-001
  test_query_readiness.py    # TC-VQ-002
  test_query_recovery.py     # TC-VQ-003 的 Python 检查
  test_query_concurrency.py  # TC-VQ-004 的 Python 检查
  vitest.config.ts
  renderer_support.tsx      # 真实 hook 的挂载与 IPC 会话替身
  query_recovery.test.tsx    # TC-VQ-003 的界面检查
  query_submission.test.tsx  # TC-VQ-001、002、004 的界面补充
  evidence/                 # 实施、调试与结果说明
  results/                  # 每轮测试的原始证据
```

测试名称携带完整业务 ID。参数化子场景使用 `TC-VQ-002 / indexing-in-progress` 等名称，保持用户确定的编号。

## 测试装置与隔离

1. `conftest.py` 显式加载 `python_backend/videorag_api.py` 并验证模块的 `__file__`。现有 `test_videorag_api/tests/support.py` 默认可能导入测试目录副本，只借鉴其依赖隔离方式，不沿用默认导入结果。
2. Flask 使用 `test_client()`；Process 使用可控制 `start/is_alive/join/terminate` 行为的替身；模型使用可切换失败/成功结果的替身。不启动真实网络、GPU 或模型进程。
3. 持久化检查使用临时目录和实际 JSON 读写。不能用只验证 Mock 调用的方式替代“旧结果已清除”或“状态已恢复”。
4. 单独检查路由错误映射时可以替换管理器；检查准入、任务登记或并发时必须使用真实管理器。每条测试注明所证明的范围。
5. worker 修改 `sys.argv` 等全局状态时需恢复；每例恢复模块全局管理器、环境变量、日志目标和 Mock。API 日志重定向到临时目录或测试日志，不写入业务目录。
6. Vitest 使用真实 hook/组件与受控 IPC 返回；借鉴 `test_renderer` 的 jsdom 和 Testing Library 配置。用 fake timers 推进轮询，卸载后清理定时器与未完成请求。
7. 对 stateful 场景使用事件和可控回调确定顺序，不依赖任意 sleep。每段等待设置保护上限，避免失败测试挂起。
8. 状态写入可能自身存在缺陷。正式业务测试保留真实失败并注明根因；为分析其他逻辑而临时替换状态写入的诊断测试，不能替代正式业务验收。

## 实现边界与运行约定

pytest 的空白查询检查隔离管理器调度方法，专门验证真实路由是否在调用管理器前拒绝输入；其他准入、恢复和并发检查使用真实管理器。正常输入对照分别验证路由下发与真实进程启动，不能把前者通过当作后者通过。

Python 使用临时目录真实读写状态文件。`ControlledProcess.start()` 只记录进程状态，`run()` 才调用真实 worker，并在 finally 中模拟进程退出；模型和 ImageBind 是依赖替身。因此检查证明的是业务调度与状态逻辑，不是操作系统真实进程回收或真实模型执行。

Vitest 实际执行 `useChat`、路由参数读取及 `utils/chat.ts` 的消息增删改和事件刷新；会话上下文、索引背景元数据和 IPC 是受控依赖。测试断言真实 hook 返回的消息和等待状态，不使用手写查询状态机，不声称覆盖整个 App、真实按钮展示或 IPC 到 Python 的联调。轮询通过 fake timers 推进，测试内确认终态后不会继续轮询。

有必要单独排查 Python 时，在仓库根目录执行：

```powershell
python -m pytest -c Vimo-desktop/test_video_query/pytest.ini Vimo-desktop/test_video_query -q
```

完整验收与留档使用本页的一键运行入口。每个 ID 的预期收集数由运行器固定检查，新增或删除检查时需同步更新 `EXPECTED`。前置启动失败用 `BLOCKED_BEFORE_WORKER` 标记，仍保留为失败，不作为 skip，也不能据此确认后续恢复/并发逻辑有缺陷。

## 当前验证结果

环境：Windows、Python 3.12.7、pytest 7.4.4、Node.js 22.13.1、Vitest 2.1.9。最终有效运行的报告位置见 [实施记录](evidence/implementation.md)。

| 业务 ID | pytest 通过/检查 | Vitest 通过/检查 | 业务结论 |
| --- | --- | --- | --- |
| TC-VQ-001 | 1/6 | 6/6 | 后端路由仍下发空白问题；前端不下发空白问题，合法 trim 对照通过 |
| TC-VQ-002 | 0/4 | 2/2 | 后端不存在会话可被意外创建并启动；未就绪会话拒绝结果不符合约定；正常启动对照被状态覆盖失败阻断 |
| TC-VQ-003 | 0/1 | 1/1 | 前端超时反馈、停止轮询、保留历史、成功重试通过；后端尚未执行到模型超时路径 |
| TC-VQ-004 | 0/1 | 1/1 | 前端连续提问和答案对应检查通过；后端尚未执行到第二次提问的并发保护 |

总计 22 个检查，11 通过、11 失败，其中 3 个失败明确发生在 worker 启动前。当前 Windows 环境中，对已有状态文件执行 `os.rename` 引发 WinError 183，阻断了正常查询启动以及恢复/并发测试的后续步骤。没有替换真实状态写入来掩盖这个问题。11 个失败不能记为 11 个独立缺陷，恢复和并发也不能记为已完成后端验证。

## AI 实践记录与完成标准

- 保存 AI 提示词、原始回答、人工审核意见、测试修改差异、被测源码提交号、原始日志和缺陷记录。
- 4 个业务 ID 全部有执行记录。一个 ID 的必要 Python/TypeScript 检查全部通过，才标记该业务用例通过。
- 业务用例数、参数组合数和脚本执行数分别统计，不把参数化数量当作新的业务 ID。
- 区分断言失败、环境/收集错误、超时和跳过；不能将测试失败全部归为产品缺陷。
- 缺陷须保留最小复现、修复前失败、修复后通过和相关回归证据；已有问题标注为 AI 辅助定位/修复，不宣称新发现。
- 未实测前不填写通过率、恢复耗时或缺陷数量；隔离测试通过不等于真实部署的整条链路已经通过。
