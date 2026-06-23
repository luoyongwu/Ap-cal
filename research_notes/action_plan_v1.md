# Luo-cal 下阶段可执行行动方案
版本：v1.1
日期：2026-06-22
修改记录：根据战略研讨补充华人用户渠道、低信号替代展示、
          首诊/复诊Reflection Rate拆分、会话恢复逻辑、
          FWM预留字段、DAN心理真实性论文规划

---

## 一、战略定位

**产品定义**：Luo-cal 不是会聊天的 AI 导师，而是认知镜子。
**核心差异**：不展示学生学了什么，而是展示学生认知状态的拓扑结构。
**目标用户（Phase 1）**：全球 AP 微积分学生，含海外华人学生。
**暂缓事项**：中国本土部署、微信生态、支付系统——待产品价值验证后再启动。

---

## 二、理论基础（已验证）

| 命题 | 验证方式 | 状态 |
|------|---------|------|
| SCL可在强推理模型上稳定实现苏格拉底教学 | 11/11 MADNESS通过 | ✓ 已验证 |
| SCL效果模型无关（Model-Agnostic） | Claude + DeepSeek双模型验证 | ✓ 已验证 |
| 裸模式下强推理模型无法自发维持苏格拉底行为 | 四条件消融矩阵 | ✓ 已验证 |
| DAN具有心理真实性（构念效度） | Reflection Rate > 80% | ○ 待验证 |
| FWM条件概率估计 | 需真实学生数据 | ○ 待验证 |

---

## 三、技术架构

### 3.1 技术栈选型

| 层次 | 选型 | 理由 |
|------|------|------|
| 后端框架 | FastAPI（async） | SCL逻辑是Python，迁移成本低；async适合IO密集型 |
| 数据库 | PostgreSQL | DAN信号schema已定义，直接建表，不走渐进路线 |
| 前端 | 极简Web（Next.js或纯HTML） | Phase 1只需登录/存档/Dashboard三个功能 |
| 部署 | Vercel + Cloudflare | 海外部署，绕开中国合规链条 |
| 模型调用 | 服务端完成 | 前端不直接调模型；SCL约束+模型调用+DAN信号记录全在FastAPI后端 |

### 3.2 核心架构原则

- 前端职责极薄，只负责展示和交互
- SCL逻辑从app.py迁移，endpoint结构一对一映射
- DAN信号第一天就写入PostgreSQL，不经过session_state过渡

### 3.3 DAN信号数据结构

每次EWM触发时写入一条记录，字段如下：

student_id, concept, signal, round, timestamp
trigger_context: { problem_type, student_input_snippet }
intercept_result: { intercepted, rounds_to_correct }

预留FWM字段（Phase 2启用，Phase 1建表时即预留）：
fwm_predicted_next_error VARCHAR  -- 预测的下一个EWM类型
fwm_prediction_accuracy BOOLEAN   -- 预测是否准确

### 3.4 会话恢复逻辑

学生关闭浏览器再打开时：

- 上次会话未完成（被SCL拦截后中断）：
  展示"继续上次的学习"，直接恢复到上次对话状态
- 上次会话已完成：
  展示"开始新练习"，同时显示DAN Dashboard v0.1链接
- 上次会话距今超过7天：
  提示"距离上次学习已过X天，是否从上次继续？"

注意：会话恢复逻辑需在Phase 1前端实现时就设计好，否则存档功能形同虚设。

---

## 四、DAN Dashboard 分版路线

### v0.1 — 诊断快照（Phase 1前半段）

**工程成本**：极低，会话内EWM信号聚合，不需要跨会话存储

**交付内容**：
- 本次会话触发了哪些EWM
- 按概念维度分组显示
- 一句话总结（用日常语言，不直接暴露Flow Reasoning等术语）
- Reflection Rate问卷（见第五节）

**低信号替代展示**（本次会话EWM信号 < 3个时）：
- 不显示诊断总结
- 改为显示："我还在学习你的思维模式。再完成几次练习后，我会给出更准确的画像。"
- 显示已收集的信号数量（如"已收集2个思维信号"）

**注意事项**：
- Dashboard底部注明"基于本次会话的观察，样本量有限"——管理预期
- 认知维度名称（Flow Reasoning等）写进配置文件，不在前端硬编码
- v0.1用日常语言描述，等Reflection Rate开放文本积累后再修正术语

### v0.2 — 跨会话趋势（Phase 2）

**前置条件**：Phase 1 Reflection Rate > 80%，PostgreSQL跨会话数据积累

**交付内容**：
- 同一EWM的历史触发频率
- 认知维度的动态变化（改善还是固化）
- 桥接建议（例："建议先巩固7.2-7.3"）
- 跨会话必须提供增量洞察，而非复读上次总结

---

## 五、核心验证指标

| 指标 | 定义 | 验证什么 | 目标值 |
|------|------|---------|--------|
| 7天留存率 | 首次使用后7天内再次打开的学生比例 | 产品是否有持续吸引力 | >40% |
| Dashboard查看率 | 登录后点进Dashboard的学生比例 | 认知镜子概念是否吸引人 | >60% |
| 每会话平均EWM触发数 | 每个学生每次会话平均触发EWM拦截次数 | DAN数据积累效率；SCL探针覆盖密度 | ≥3个 |
| EWM触发后继续对话轮数 | 被拦截后学生继续对话的平均轮数 | SCL拦截是否产生真实认知参与 | >2轮 |
| 重复EWM行为改变率 | 同一EWM第二次触发时学生更快纠正的比例 | SCL是否产生真实教学效果 | >30% |
| 首诊Reflection Rate | 首次Dashboard看完后选"很像"的比例 | DAN初始诊断的心理真实性 | >80% |
| 复诊Reflection Rate | 第二次及以上Dashboard看完后选"很像"的比例 | DAN是否提供增量洞察而非复读 | >70% |

**注意**：若复诊率显著低于首诊率，说明DAN在重复诊断，指导v0.2必须提供跨会话增量信息。

### Reflection Rate 问卷设计

Dashboard展示后，系统只问一句话：

你觉得这个描述像你吗？

按钮：很像 / 部分像 / 不像

可选开放文本框（两个引导问题）：
1. 哪里描述得不准确？
2. 你觉得用___来描述你的模式，有没有更好的说法？

数据用途：
- 定量：Reflection Rate作为DAN构念效度的核心指标
- 定性：开放文本修正维度命名，反向验证认知维度分类
- 学术：若首诊Reflection Rate > 80%，可在论文中声明DAN具有Psychological Validity

---

## 六、分阶段路线图

### Phase 1（第1个月）— 验证认知镜子

**目标**：100个真实用户，验证DAN诊断快照是否有心理真实性

**交付物**：
- [ ] FastAPI后端，SCL逻辑从app.py迁移
- [ ] PostgreSQL建表（DAN信号schema + FWM预留字段）
- [ ] 用户登录与会话存档（含会话恢复逻辑）
- [ ] DAN Dashboard v0.1（诊断快照 + 低信号替代展示）
- [ ] Reflection Rate问卷（首诊/复诊分别记录）

**暂不做**：支付、小程序、中国部署、跨会话趋势分析

**种子用户渠道**：
- 北美：Reddit（r/APStudents）、Discord AP社群、CollegeConfidential
- 华人：小红书AP标签、微信公众号AP备考群、国际学校家长群

**华人渠道的战略价值**：Phase 1的海外华人用户是Phase 4中国商业化的种子用户，同时可通过"打赏或赞助"方式初步探测付费意愿，不需要完整支付系统。

### Phase 2（第2-3个月）— DAN Memory Alpha

**前置条件**：Phase 1首诊Reflection Rate > 80%

**交付物**：
- [ ] 跨会话DAN信号积累与时序分析
- [ ] DAN Dashboard v0.2（跨会话趋势 + 增量洞察）
- [ ] 认知维度动态变化可视化
- [ ] 桥接概念建议系统

**学术产出**：Learning Analytics数据，回答哪些EWM最常见、哪些桥接概念最有效

### Phase 3（第4-5个月）— 自适应SCL

**前置条件**：Phase 2积累足够DAN信号

**交付物**：
- [ ] SCL根据DAN状态动态调整拦截策略
  - 第1次犯错：苏格拉底反问
  - 第3次犯错：更直接引导
  - 第5次犯错：显式指出

**学术贡献**：从"证明约束层可行"升级为"证明约束层可以学习"

### Phase 4（6个月后）— 商业化

**前置条件**：Phase 3验证自适应SCL有效

**交付物**：
- [ ] 微信H5 + 阿里云迁移
- [ ] ICP备案与内容合规
- [ ] 微信支付接入
- [ ] 会员体系

---

## 七、学术任务（与Phase 1并行）

| 任务 | 优先级 | 说明 |
|------|--------|------|
| arXiv论文重写 | P1 | 加入四条件消融矩阵、DeepSeek对照、Benevolent Leakage独立成节 |
| SCL消融矩阵扩展 | P2 | 加入Strong Prompt条件，完成三路对比 |
| 模型无关性补充验证 | P3 | 加入Qwen或Kimi |
| Cognitive Signal提取实现 | P4 | EWM触发时写入结构化信号，Phase 1基础设施 |
| DAN心理真实性论文 | P5 | 标题候选：Reflection Rate as a Measure of Psychological Validity in AI-Generated Cognitive Diagnostics；发表目标：Learning @ Scale、AIED或CHI Late-Breaking Work；Phase 1开始时按论文标准收集数据 |

---

## 八、决策依据与修改记录

| 版本 | 日期 | 修改内容 | 触发原因 |
|------|------|---------|---------|
| v1.0 | 2026-06-21 | 初稿 | 四条件消融完成后的战略研讨 |
| v1.1 | 2026-06-22 | 增加华人用户渠道；低信号替代展示；首诊/复诊Reflection Rate拆分；会话恢复逻辑；PostgreSQL预留FWM字段；DAN心理真实性论文规划；认知维度术语配置化原则 | 执行纲领审阅后的修改意见 |

---

*所有后续工作从此文档出发。重大决策修改在第八节留痕。*
*生成时间：2026-06-22 | 硅基智库*
