import os
import re
import json
import streamlit as st
from agno.agent import Agent
from agno.models.perplexity import Perplexity
from agno.tools.arxiv import ArxivTools
from agno.tools.reasoning import ReasoningTools
from agno.run.response import RunResponse, RunEvent

# ==== 持久化相关函数 ====
REPORT_FILE = "weekly_report.json"

def save_weekly_report():
    data = {
        "response_content": st.session_state.get("response_content", ""),
        "citations_html": st.session_state.get("citations_html", ""),
        "paper_titles": st.session_state.get("paper_titles", []),
        "paper_abstracts": st.session_state.get("paper_abstracts", []),
        "paper_urls": st.session_state.get("paper_urls", []),
    }
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_weekly_report():
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            st.session_state.response_content = data.get("response_content", "")
            st.session_state.citations_html = data.get("citations_html", "")
            st.session_state.paper_titles = data.get("paper_titles", [])
            st.session_state.paper_abstracts = data.get("paper_abstracts", [])
            st.session_state.paper_urls = data.get("paper_urls", [])

# ==== 启动时自动加载持久化内容 ====
load_weekly_report()

# 设置API密钥
api_key = os.environ.get("OPENAI_API_KEY", "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")
os.environ["OPENAI_API_KEY"] = api_key

st.title("ArXiv 学术周报生成器")
st.write("根据关键词自动生成最新arXiv论文周报")

# 初始化关键词状态
if "keywords" not in st.session_state:
    st.session_state.keywords = ["通信", "AI", "6G", "LLM", "Agent"]

# 初始化内容状态
if "response_content" not in st.session_state:
    st.session_state.response_content = ""
if "citations_html" not in st.session_state:
    st.session_state.citations_html = ""
if "paper_titles" not in st.session_state:
    st.session_state.paper_titles = []
if "paper_abstracts" not in st.session_state:
    st.session_state.paper_abstracts = []
if "paper_urls" not in st.session_state:
    st.session_state.paper_urls = []

st.subheader("管理关键词")
try:
    from streamlit_tags import st_tags
    st.session_state.keywords = st_tags(
        label='输入关键词:',
        text='输入后按回车添加',
        value=st.session_state.keywords,
        suggestions=['量子计算', '神经网络', '强化学习'],
        maxtags=10,
        key="keywords_input"
    )
except ImportError:
    keyword_cols = st.columns(5)
    for i, kw in enumerate(st.session_state.keywords):
        with keyword_cols[i % 5]:
            if st.button(f"❌ {kw}", key=f"del_{i}"):
                st.session_state.keywords.remove(kw)
                st.experimental_rerun()
    col1, col2 = st.columns([3, 1])
    with col1:
        new_keyword = st.text_input("添加新关键词")
    with col2:
        if st.button("添加") and new_keyword:
            st.session_state.keywords.append(new_keyword)
            st.experimental_rerun()

tab1, tab3, tab2 = st.tabs(["📄 学术周报", "📑 论文详情", "🔗 参考文献"])

# ==== 自动生成周报（仅首次，无内容时） ====
if not st.session_state.response_content and st.session_state.keywords:
    with st.spinner("正在自动生成学术周报..."):
        agent = Agent(
            model=Perplexity(id="sonar-pro"),
            tools=[
                ArxivTools(search_arxiv=True, read_arxiv_papers=True),
                ReasoningTools(add_instructions=True)
            ],
            instructions=[
                "根据提供的关键词，检索近一周arXiv上相关论文，筛选高相关性内容。",
                "用表格列出论文标题、作者、发表时间、摘要要点和链接（用表格展示）",
                "正文中引用论文仅用编号标记，在[编号]标记中插入超链接。",
                "最后给出趋势分析和简要点评。"
            ],
            markdown=True,
            show_tool_calls=True
        )
        keywords_str = ", ".join(st.session_state.keywords)
        prompt = f"""
        请根据如下关键词，生成一份近一周arXiv论文学术周报，内容包括：
        1. 论文标题、作者、发表时间、摘要要点和链接(用表格展示)
        2. 研究趋势简要分析
        3. 学术热点点评
        关键词：{keywords_str}
        """

        # 清空旧内容
        st.session_state.response_content = ""
        st.session_state.citations_html = ""
        st.session_state.paper_titles = []
        st.session_state.paper_abstracts = []
        st.session_state.paper_urls = []

        response_content = ""
        citations_html = ""

        # 这里不再用 placeholder，直接写入 session_state
        for resp in agent.run(message=prompt, stream=True):
            if isinstance(resp, RunResponse) and resp.event == RunEvent.run_response and isinstance(resp.content, str):
                response_content += resp.content
            if resp.citations and resp.citations.urls:
                citations_html = "<ol>"
                for citation in resp.citations.urls:
                    if citation.url:
                        citations_html += f'<li><a href="{citation.url}" target="_blank">{citation.title or citation.url}</a></li>'
                citations_html += "</ol>"

        # 写入 session_state
        st.session_state.response_content = response_content
        st.session_state.citations_html = citations_html

        # 提取论文标题、摘要、链接
        table_pattern = r"\|(.+?)\|\s*\n\|(?:[-:\s|]+)\|\s*\n((?:\|.*\|\s*\n?)+)"
        match = re.search(table_pattern, response_content, re.DOTALL)
        paper_titles = []
        paper_abstracts = []
        paper_urls = []
        if match:
            table_body = match.group(2)
            for line in table_body.strip().split("\n"):
                cols = [col.strip() for col in line.strip().strip("|").split("|")]
                if cols:
                    paper_titles.append(cols[0])
                    if len(cols) > 3:
                        paper_abstracts.append(cols[3])
                    else:
                        paper_abstracts.append("")
                    if len(cols) > 4:
                        paper_urls.append(cols[4])
                    else:
                        paper_urls.append("")
        st.session_state.paper_titles = paper_titles
        st.session_state.paper_abstracts = paper_abstracts
        st.session_state.paper_urls = paper_urls

        # === 自动保存 ===
        save_weekly_report()

# ==== 用户主动点击生成按钮 ====
if st.button("生成学术周报", type="primary"):
    if not st.session_state.keywords:
        st.error("请至少添加一个关键词")
    else:
        progress = st.progress(0)
        status = st.empty()
        status.info("开始处理...")

        agent = Agent(
            model=Perplexity(id="sonar-pro"),
            tools=[
                ArxivTools(search_arxiv=True, read_arxiv_papers=True),
                ReasoningTools(add_instructions=True)
            ],
            instructions=[
                "根据提供的关键词，检索近一周arXiv上相关论文，筛选高相关性内容。",
                "用表格列出论文标题、作者、发表时间、摘要要点和链接（用表格展示）",
                "正文中引用论文仅用编号标记，在[编号]标记中插入超链接。",
                "最后给出趋势分析和简要点评。"
            ],
            markdown=True,
            show_tool_calls=True
        )
        keywords_str = ", ".join(st.session_state.keywords)
        prompt = f"""
        请根据如下关键词，生成一份近一周arXiv论文学术周报，内容包括：
        1. 论文标题、作者、发表时间、摘要要点和链接(用表格展示)
        2. 研究趋势简要分析
        3. 学术热点点评
        关键词：{keywords_str}
        """

        # 清空旧内容
        st.session_state.response_content = ""
        st.session_state.citations_html = ""
        st.session_state.paper_titles = []
        st.session_state.paper_abstracts = []
        st.session_state.paper_urls = []

        response_content = ""
        citations_html = ""

        try:
            status.text("正在搜索ArXiv论文...")
            progress.progress(10)

            for i, resp in enumerate(agent.run(message=prompt, stream=True)):
                if isinstance(resp, RunResponse):
                    progress_value = min(85, 10 + (i * 2))
                    progress.progress(progress_value)

                    if progress_value < 30:
                        status.text("正在搜索ArXiv论文...")
                    elif progress_value < 60:
                        status.text("正在分析论文内容...")
                    else:
                        status.text("正在生成周报...")
                    if resp.event == RunEvent.run_response and isinstance(resp.content, str):
                        response_content += resp.content

                    if resp.citations and resp.citations.urls:
                        citations_html = "<ol>"
                        for citation in resp.citations.urls:
                            if citation.url:
                                citations_html += f'<li><a href="{citation.url}" target="_blank">{citation.title or citation.url}</a></li>'
                        citations_html += "</ol>"

            # 生成完成，进度100%
            progress.progress(100)
            status.success("✅ 学术周报生成完成!")

            # 写入 session_state
            st.session_state.response_content = response_content
            st.session_state.citations_html = citations_html if citations_html else ""

            # 提取论文标题、摘要、链接
            table_pattern = r"\|(.+?)\|\s*\n\|(?:[-:\s|]+)\|\s*\n((?:\|.*\|\s*\n?)+)"
            match = re.search(table_pattern, response_content, re.DOTALL)
            paper_titles = []
            paper_abstracts = []
            paper_urls = []
            if match:
                table_body = match.group(2)
                for line in table_body.strip().split("\n"):
                    cols = [col.strip() for col in line.strip().strip("|").split("|")]
                    if cols:
                        paper_titles.append(cols[0])
                        if len(cols) > 3:
                            paper_abstracts.append(cols[3])
                        else:
                            paper_abstracts.append("")
                        if len(cols) > 4:
                            paper_urls.append(cols[4])
                        else:
                            paper_urls.append("")
            st.session_state.paper_titles = paper_titles
            st.session_state.paper_abstracts = paper_abstracts
            st.session_state.paper_urls = paper_urls

            # === 持久化保存 ===
            save_weekly_report()

        except Exception as e:
            progress.progress(100)
            status.error(f"生成过程中发生错误: {str(e)}")

# =================== TAB 渲染 ===================

with tab1:
    # 每次渲染都根据 session_state 展示内容
    if st.session_state.response_content:
        st.markdown(st.session_state.response_content)
    else:
        st.markdown("请先生成学术周报。")

with tab2:
    st.markdown(st.session_state.citations_html or "暂无参考文献。", unsafe_allow_html=True)

with tab3:
    if st.session_state.paper_titles:
        for idx, title in enumerate(st.session_state.paper_titles):
            abstract = st.session_state.paper_abstracts[idx] if idx < len(st.session_state.paper_abstracts) else ""
            url = st.session_state.paper_urls[idx] if idx < len(st.session_state.paper_urls) else ""
            expanded_key = f"expander_{idx}"
            if expanded_key not in st.session_state:
                st.session_state[expanded_key] = False

            chat_key = f"chat_history_{idx}"
            if chat_key not in st.session_state:
                default_prompt = f"""你是一位专业的科研助理，擅长深入解读学术论文。请根据以下论文链接，联网检索并阅读论文原文，提供详细的技术解读。解读内容应包括：

- 研究背景与问题
- 研究方法与技术路线
- 主要创新点
- 实验设计与结果
- 研究结论及其学术与实际意义

请用中文撰写，面向领域内专家，内容准确且深入。

论文标题：{title}
论文链接：{url}

请给出详细解读：
"""
                st.session_state[chat_key] = [
                    {"role": "assistant", "content": default_prompt}
                ]

            with st.expander(f"{idx+1}. {title}", expanded=st.session_state[expanded_key]):
                if url:
                    st.markdown(f"**摘要：** {abstract}\n\n**链接：** [{url}]")
                else:
                    st.markdown(f"**摘要：** {abstract}\n\n**链接：** 暂无链接")

                for msg in st.session_state[chat_key]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

                user_input = st.chat_input("请输入你想针对本论文提问的问题…", key=f"chat_input_{idx}")
                if user_input:
                    st.session_state[chat_key].append({"role": "user", "content": user_input})

                    agent = Agent(
                        model=Perplexity(id="sonar-pro"),
                        tools=[
                            ArxivTools(search_arxiv=False, read_arxiv_papers=False),
                            ReasoningTools(add_instructions=True)
                        ],
                        instructions=[],
                        markdown=True,
                        show_tool_calls=False
                    )
                    prompt = "\n".join(
                        [f"{m['role']}: {m['content']}" for m in st.session_state[chat_key]]
                    )
                    response_content = ""
                    chat_placeholder = st.empty()
                    with st.chat_message("assistant"):
                        for resp in agent.run(message=prompt, stream=True):
                            if isinstance(resp, RunResponse) and resp.event == RunEvent.run_response and isinstance(resp.content, str):
                                response_content += resp.content
                                chat_placeholder.markdown(response_content)
                    st.session_state[chat_key].append({"role": "assistant", "content": response_content})
    else:
        st.write("未检测到论文标题表格，无法展示论文详情。")
