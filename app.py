
import streamlit as st
from anthropic import Anthropic

MODEL_NAME = "claude-sonnet-4-20250514"
st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

# 1. 4 Units 全量课程矩阵
UNITS = {
    "Unit 1: 极限与连续": ["1.1 极限简介", "1.2 极限计算", "1.3 连续性", "1.4 渐近线"],
    "Unit 2: 导数定义": ["2.1 导数定义", "2.2 可导与连续", "2.3 导数图像", "2.4 高阶导数"],
    "Unit 3: 求导法则": ["3.1 链式法则", "3.2 隐函数求导", "3.3 反函数求导", "3.4 参数方程求导"],
    "Unit 4: 导数应用": ["4.1 极值定理", "4.2 中值定理", "4.3 相关变化率", "4.4 线性近似"]
}

# 2. 状态初始化
for k, v in {
    "messages": [], "curr_unit": "Unit 1: 极限与连续", "curr_concept": "1.1 极限简介",
    "lang": "中文", "status": "就绪", "is_confirmed": False
}.items():
    if k not in st.session_state: st.session_state[k] = v

# 3. 侧边栏：配置页 (含确认机制)
with st.sidebar:
    st.title("⚙️ 配置页")
    st.session_state.lang = st.radio("语言切换", ["中文", "English"])
    new_unit = st.selectbox("选择 Unit", list(UNITS.keys()))
    new_concept = st.selectbox("选择 Concept", UNITS[new_unit])
    if st.button("✅ 确认配置"):
        st.session_state.curr_unit = new_unit
        st.session_state.curr_concept = new_concept
        st.session_state.is_confirmed = True
        st.session_state.status = "已锁定"
        st.rerun()

# 4. 主界面：状态栏与测试输入
st.title(f"🎓 Luo-cal: {st.session_state.curr_concept}")
st.metric("系统状态", st.session_state.status)

if not st.session_state.is_confirmed:
    st.warning("请在配置页确认配置后开始测试。")
    st.stop()

# 5. 测试交互区
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("输入测试题..."):
    st.session_state.status = "正在分析..."
    st.session_state.messages.append({"role": "user", "content": prompt})
    # 模拟 API 交互
    st.session_state.messages.append({"role": "assistant", "content": f"导师反馈 (Lang:{st.session_state.lang}): [STATUS: GUIDING]"})
    st.session_state.status = "就绪"
    st.rerun()
