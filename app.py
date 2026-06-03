
import streamlit as st
from anthropic import Anthropic
import json

MODEL_NAME = "claude-sonnet-4-6"

st.set_page_config(page_title="Luo-cal 高速国际化版", layout="wide")

# --- 状态初始化 ---
if "messages" not in st.session_state: st.session_state.messages = []
if "ENV_CLAUDE_KEY" not in st.session_state: st.session_state.ENV_CLAUDE_KEY = ""
if "curr_unit" not in st.session_state: st.session_state.curr_unit = "Unit 1: Limits & Continuity"
if "curr_concept" not in st.session_state: st.session_state.curr_concept = "1.1 Limits Intro"
if "curr_lang" not in st.session_state: st.session_state.curr_lang = "Chinese"

# 双语核心内容矩阵映射
CONTENT_MATRIX = {
    "Chinese": {
        "Unit 1: Limits & Continuity": ["1.1 极限入门", "1.2 渐近线", "1.3 连续性", "1.4 夹逼定理", "1.5 介值定理"],
        "Unit 2: Derivatives": ["2.1 导数定义", "2.2 幂/积法则", "2.3 链式法则", "2.4 高阶导数"]
    },
    "English": {
        "Unit 1: Limits & Continuity": ["1.1 Limits Intro", "1.2 Asymptotes", "1.3 Continuity", "1.4 Squeeze Theorem", "1.5 Intermediate Value Theorem"],
        "Unit 2: Derivatives": ["2.1 Derivative Definition", "2.2 Power/Product Rules", "2.3 Chain Rule", "2.4 Higher-Order"]
    }
}

# 侧边栏 UI 语言字典
UI_LABELS = {
    "Chinese": {
        "title": "🎓 Luo-cal 教学控制台",
        "key_active": "🟢 密钥已激活",
        "key_warn": "🔴 请输入 API Key",
        "select_unit": "📂 选择 Unit:",
        "select_concept": "🎯 选择 Concept:",
        "lang_label": "🌐 语言:",
        "placeholder": "请输入你的解答或问题...",
        "next_btn": "▶️ 下一题",
        "wait_msg": "🌐 正在为您提供高速无缝语言转换...",
        "think_msg": "⏳ 正在思考..."
    },
    "English": {
        "title": "🎓 Luo-cal Console",
        "key_active": "🟢 Key Activated",
        "key_warn": "🔴 Enter API Key",
        "select_unit": "📂 Select Unit:",
        "select_concept": "🎯 Select Concept:",
        "lang_label": "🌐 Language:",
        "placeholder": "Enter your answer or question...",
        "next_btn": "▶️ Next Problem",
        "wait_msg": "🌐 Fast translating interface language...",
        "think_msg": "⏳ Thinking..."
    }
}

# --- 侧边栏渲染 (全动态国际化) ---
ui = UI_LABELS[st.session_state.curr_lang]

st.sidebar.title(ui["title"])
key_input = st.sidebar.text_input("🔑 API Key:", type="password", placeholder="sk-ant-api03-...")
if key_input.strip(): st.session_state.ENV_CLAUDE_KEY = key_input.strip()

if st.session_state.ENV_CLAUDE_KEY:
    st.sidebar.success(ui["key_active"])
else:
    st.sidebar.warning(ui["key_warn"])

# 确保侧边栏数据源跟随语言联动
matrix_source = CONTENT_MATRIX[st.session_state.curr_lang]
selected_unit = st.sidebar.selectbox(ui["select_unit"], list(matrix_source.keys()))

# 根据当前选中的单元，获取对应的概念列表
concepts_list = matrix_source[selected_unit]
# 智能索引锚定：防止语言切换时数组越界
try:
    old_index = CONTENT_MATRIX["Chinese" if st.session_state.curr_lang == "English" else "English"][selected_unit].index(st.session_state.curr_concept)
    default_index = old_index if old_index < len(concepts_list) else 0
except:
    default_index = 0

selected_concept = st.sidebar.selectbox(ui["select_concept"], concepts_list, index=default_index)
lang = st.sidebar.radio(ui["lang_label"], ["Chinese", "English"], index=0 if st.session_state.curr_lang == "Chinese" else 1)

# --- 核心辅助函数：打包单次闪电翻译网关 ---
def fast_translate_history(target_lang):
    if not st.session_state.messages or not st.session_state.ENV_CLAUDE_KEY:
        return
    
    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
    
    # ⚡ 速度优化核心：将整个会话打包成单个 JSON 字符串一次性发送
    raw_payload = json.dumps(st.session_state.messages, ensure_ascii=False)
    
    prompt = f"""You are a professional translator. Translate the following JSON array of chat messages into {'English' if target_lang == 'English' else 'Simplified Chinese (简体中文)'} for an AP Calculus learning system.
Rules:
1. Return ONLY the translated JSON array matching the original structure. Do not include markdown code blocks (like ```json), do not include any intro or outro text.
2. Keep all LaTeX math expressions (e.g., $...$, $$...$$) EXACTLY unchanged.
3. Keep the "role" fields ("user" or "assistant") exactly as they are.

JSON to translate:
{raw_payload}"""

    with st.spinner(UI_LABELS[st.session_state.curr_lang]["wait_msg"]):
        try:
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            clean_text = response.content[0].text.strip()
            # 清洗可能夹带的 markdown 标记
            if clean_text.startswith("
```"):
                clean_text = clean_text.split("\n", 1)[1].rsplit("\n", 1)[0]
            st.session_state.messages = json.loads(clean_text)
        except Exception as e:
            st.error(f"Translation sync failed: {e}")

# --- 状态变动拦截总线 ---
# 场景 A: Unit 或 Concept 切换 -> 清空历史触发新题自启
if selected_unit != st.session_state.curr_unit or selected_concept != st.session_state.curr_concept:
    st.session_state.curr_unit = selected_unit
    st.session_state.curr_concept = selected_concept
    st.session_state.messages = []
    st.rerun()

# 场景 B: 仅语言切换 -> 触发闪电全量对译，同步更新左侧菜单状态
if lang != st.session_state.curr_lang:
    if st.session_state.messages:
        fast_translate_history(lang)
    # 反向同步概念标识
    current_idx = CONTENT_MATRIX[st.session_state.curr_lang][selected_unit].index(selected_concept)
    st.session_state.curr_concept = CONTENT_MATRIX[lang][selected_unit][current_idx]
    st.session_state.curr_lang = lang
    st.rerun()

# 主界面标题呈现
st.title(f"{selected_unit} - {selected_concept}")

# --- AI 对话引擎 ---
def get_ai_response():
    if not st.session_state.ENV_CLAUDE_KEY:
        st.warning("⚠️ Please enter API Key")
        st.stop()
        
    client = Anthropic(api_key=st.session_state.ENV_CLAUDE_KEY)
    system_msg = f"You are an AP Calculus tutor. Respond entirely in {'Chinese (简体中文)' if st.session_state.curr_lang == 'Chinese' else 'English'}. Rules: Use LaTeX for all math expressions. Use Socratic method: guide the student with hints and questions, never give away the full answer directly. Ask only one question at a time."
    
    with st.spinner(ui["think_msg"]):
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1500,
            system=system_msg,
            messages=st.session_state.messages
        )
    return response.content[0].text

# --- 教学主业务流 ---
# 1. 系统首题与首问主动热启动 (优化：由大模型亲自生成亲切的第一问)
if not st.session_state.messages:
    init_prompt = (
        f"Please act as an AP Calculus tutor. Give me the first AP-style challenge problem for '{st.session_state.curr_concept}' "
        f"in {'Chinese' if st.session_state.curr_lang == 'Chinese' else 'English'}. "
        f"Adopt the Socratic method from your very first sentence: welcome me briefly, state the problem clearly, and ask the first guiding question."
    )
    # 模拟用户隐式点火
    st.session_state.messages.append({"role": "user", "content": init_prompt})
    res = get_ai_response()
    if res:
        # 将点火 prompt 替换为标准优雅的开场，避免前台暴露系统指令
        st.session_state.messages[0]["content"] = "Let's start!" if st.session_state.curr_lang == "English" else "让我们开始吧！"
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()

# 2. 渲染历史对话
for msg in st.session_state.messages:
    if msg["content"] in ["Let's start!", "让我们开始吧！"]: 
        continue # 隐藏点火标志语，让 UI 干净美观
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 3. 学生答题交互
if prompt := st.chat_input(ui["placeholder"]):
    st.session_state.messages.append({"role": "user", "content": prompt})
    res = get_ai_response()
    if res:
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()

# 4. 下一题换题按钮
if st.button(ui["next_btn"]):
    next_prompt = f"请针对 {st.session_state.curr_concept} 继续出下一道 AP 难度习题。" if st.session_state.curr_lang == "Chinese" else f"Please give me the next AP-level problem for {st.session_state.curr_concept}."
    st.session_state.messages.append({"role": "user", "content": next_prompt})
    res = get_ai_response()
    if res:
        st.session_state.messages.append({"role": "assistant", "content": res})
        st.rerun()
