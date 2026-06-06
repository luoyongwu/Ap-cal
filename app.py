
import streamlit as st
from anthropic import Anthropic

st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

# 1. 课程矩阵
UNITS = {
    "Unit 1: 极限与连续": ["1.1 极限简介", "1.2 极限计算", "1.3 连续性", "1.4 渐近线"],
    "Unit 2: 导数定义": ["2.1 导数定义", "2.2 可导与连续", "2.3 导数图像", "2.4 高阶导数"],
    "Unit 3: 求导法则": ["3.1 链式法则", "3.2 隐函数求导", "3.3 反函数求导", "3.4 参数方程求导"],
    "Unit 4: 导数应用": ["4.1 极值定理", "4.2 中值定理", "4.3 相关变化率", "4.4 线性近似"]
}

# 2. 状态初始化
if "key_ok" not in st.session_state: st.session_state.key_ok = False
if "config_ok" not in st.session_state: st.session_state.config_ok = False
if "messages" not in st.session_state: st.session_state.messages = []
if "status" not in st.session_state: st.session_state.status = "未就绪"

# 3. 侧边栏：配置页 (锁死配置)
with st.sidebar:
    st.title("⚙️ 配置页")
    api_key_input = st.text_input("🔑 Claude API Key", type="password")
    if st.button("✅ 确认 Key"):
        if api_key_input: 
            st.session_state.key_ok = True
            st.success("Key 已锁定")
        else: st.error("Key 不能为空")
    
    st.divider()
    unit = st.selectbox("选择 Unit", list(UNITS.keys()))
    concept = st.selectbox("选择 Concept", UNITS[unit])
    if st.button("✅ 确认配置"):
        st.session_state.curr_concept = concept
        st.session_state.config_ok = True
        st.success(f"已锁定: {concept}")

# 4. 主界面：红绿状态显示
st.title(f"🎓 Luo-cal: {st.session_state.get('curr_concept', '待配置')}")
if st.session_state.key_ok and st.session_state.config_ok:
    st.success("系统状态: 就绪 (配置已完成)")
    st.session_state.status = "就绪"
else:
    st.error("系统状态: 未就绪 (需完成 Key 与配置确认)")
    st.session_state.status = "未就绪"

# 5. 测试交互区
st.subheader("📝 测试与交互")
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("输入测试题..."):
    if not (st.session_state.key_ok and st.session_state.config_ok):
        st.warning("请先完成配置确认！")
    else:
        st.session_state.status = "正在工作，稍后..."
        st.info(st.session_state.status)
        st.session_state.messages.append({"role": "user", "content": prompt})
        # 模拟交互
        st.session_state.messages.append({"role": "assistant", "content": "导师反馈: [STATUS: GUIDING]"})
        st.session_state.status = "就绪"
        st.rerun()
