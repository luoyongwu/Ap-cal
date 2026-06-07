import streamlit as st
from anthropic import Anthropic
import base64

MODEL_NAME = "claude-sonnet-4-6"
st.set_page_config(page_title="Luo-cal AP微积分导师", layout="wide")

# 概念矩阵 (包含 Unit 1-4)
UNITS = {
   "Unit 1: 极限与连续": {
       "1.1 极限简介": "1.1", "1.2 极限计算": "1.2",
       "1.3 连续性": "1.3", "1.4 渐近线": "1.4"
   },
   "Unit 2: 导数定义": {
       "2.1 导数定义": "2.1", "2.2 可导与连续": "2.2",
       "2.3 导数图像": "2.3", "2.4 高阶导数": "2.4"
   },
   "Unit 3: 求导法则": {
       "3.1 链式法则": "3.1", "3.2 隐函数求导": "3.2",
       "3.4 反函数求导": "3.4"
   },
   "Unit 4: 导数应用": {
       "4.1 极值定理": "4.1", "4.2 中值定理": "4.2",
       "4.3 相关变化率": "4.3"
   },
}

# 辅助配置初始化
for k, v in {
   "messages": [], "api_key": "", "key_confirmed": False,
   "curr_unit": "Unit 1: 极限与连续", "curr_concept": "1.1 极限简介",
   "mastery_scores": {}, "mastery_ready": False, "last_summary": "",
}.items():
   if k not in st.session_state: st.session_state[k] = v

with st.sidebar:
   st.title("⚙️ 配置页")
   key_input = st.text_input("🔑 Claude API Key", type="password", value=st.session_state.api_key)
   if st.button("✅ 确认 Key"):
       if key_input.startswith("sk-"):
           st.session_state.api_key = key_input
           st.session_state.key_confirmed = True
       else: st.error("Key 格式错误")

   selected_unit = st.selectbox("选择 Unit", list(UNITS.keys()), index=list(UNITS.keys()).index(st.session_state.curr_unit))
   selected_concept = st.selectbox("选择 Concept", list(UNITS[selected_unit].keys()))
   
   if selected_unit != st.session_state.curr_unit or selected_concept != st.session_state.curr_concept:
       st.session_state.update({"curr_unit": selected_unit, "curr_concept": selected_concept, "messages": [], "last_summary": "", "mastery_ready": False})
       st.rerun()

def get_ai_response(extra_content=None):
   client = Anthropic(api_key=st.session_state.api_key)
   msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if isinstance(m.get("content"), (str, list))]
   if extra_content: msgs.append({"role": "user", "content": extra_content})
   with st.spinner("⏳ 导师思考中…"):
       return client.messages.create(model=MODEL_NAME, max_tokens=1500, messages=msgs).content[0].text

if not st.session_state.messages and st.session_state.key_confirmed:
   st.session_state.messages.append({"role": "assistant", "content": get_ai_response(f"请针对 {st.session_state.curr_concept} 出一道题。")})
   st.rerun()

for m in st.session_state.messages:
   with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("输入回答..."):
   st.session_state.messages.append({"role": "user", "content": prompt})
   st.session_state.messages.append({"role": "assistant", "content": get_ai_response()})
   st.rerun()
