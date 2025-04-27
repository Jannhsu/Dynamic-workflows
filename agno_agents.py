import os
import streamlit as st
from agno.agent import Agent
from agno.models.perplexity import Perplexity
from agno.models.openai import OpenAIChat
from agno.tools.arxiv import ArxivTools
from agno.tools.reasoning import ReasoningTools
from agno.run.response import RunResponse, RunEvent

# 推荐用 st.secrets 读取
api_key = st.secrets["OPENAI_API_KEY"]

# 页面设置
st.title("ArXiv 学术周报生成器")
st.write("根据关键词自动生成最新arXiv论文周报")

# 初始化关键词状态
if "keywords" not in st.session_state:
    st.session_state.keywords = ["通信", "AI", "6G", "LLM", "Agent"]

# 关键词管理部分
st.subheader("管理关键词")

# 尝试使用streamlit-tags组件(如已安装)
try:
    from streamlit_tags import st_tags
    
    # 使用st_tags提供更好的标签UI体验
    keywords = st_tags(
        label='输入关键词:',
        text='输入后按回车添加',
        value=st.session_state.keywords,
        suggestions=['量子计算', '神经网络', '强化学习'],
        maxtags=10
    )
    st.session_state.keywords = keywords
    
except ImportError:
    # 如未安装streamlit-tags，使用基础UI
    # 显示当前关键词
    keyword_cols = st.columns(5)
    for i, kw in enumerate(st.session_state.keywords):
        with keyword_cols[i % 5]:
            if st.button(f"❌ {kw}", key=f"del_{i}"):
                st.session_state.keywords.remove(kw)
                st.experimental_rerun()

    # 添加新关键词
    col1, col2 = st.columns([3, 1])
    with col1:
        new_keyword = st.text_input("添加新关键词")
    with col2:
        if st.button("添加") and new_keyword:
            st.session_state.keywords.append(new_keyword)
            st.experimental_rerun()

# 生成周报按钮
if st.button("生成学术周报", type="primary"):
    if not st.session_state.keywords:
        st.error("请至少添加一个关键词")
    else:
        # 显示进度信息
        progress = st.progress(0)
        status = st.empty()
        status.info("开始处理...")
        
        # 创建Agno代理
        agent = Agent(
            model=OpenAIChat(
                id="openai/gpt-4o-mini",
                api_key=api_key,
                base_url=st.secrets.get("OPENAI_API_BASE", None),
                default_headers={"Authorization": f"Bearer {api_key}"},
            ),
            tools=[
                ArxivTools(search_arxiv=True, read_arxiv_papers=True),
                ReasoningTools(add_instructions=True)
            ],
            instructions=[
                "根据提供的关键词，检索近一周arXiv上相关论文，筛选高相关性内容。",
                "用表格列出论文标题、作者、发表时间、摘要要点和引用编号（如[1]、[2]）。",
                "正文中引用论文仅用编号标记，在[编号]标记中插入超链接。",
                "最后给出趋势分析和简要点评。"
            ],
            markdown=True,
            show_tool_calls=True
        )
        
        # 生成提示词
        keywords_str = ", ".join(st.session_state.keywords)
        prompt = f"""
        请根据如下关键词，生成一份近一周arXiv论文学术周报，内容包括：
        1. 论文标题（插入超链接）、作者、发表时间、摘要要点
        2. 研究趋势简要分析
        3. 学术热点点评
        
        关键词：{keywords_str}
        """
        
        # 创建选项卡展示不同内容
        tab1, tab2 = st.tabs(["📄 学术周报", "🔗 参考文献"])
        
        # 初始化内容容器
        with tab1:
            response_placeholder = st.empty()
            
        with tab2:
            citations_placeholder = st.empty()
        
        # 初始化响应内容
        response_content = ""
        
        try:
            # 处理进度更新
            status.text("正在搜索ArXiv论文...")
            progress.progress(10)
            
            # 运行代理并流式更新内容
            for i, resp in enumerate(agent.run(message=prompt, stream=True)):
                if isinstance(resp, RunResponse):
                    # 更新进度
                    if i % 5 == 0:
                        progress_value = min(85, 10 + (i * 2))
                        progress.progress(progress_value)
                    
                    # 根据进度阶段更新状态
                    if progress_value < 30:
                        status.text("正在搜索ArXiv论文...")
                    elif progress_value < 60:
                        status.text("正在分析论文内容...")
                    else:
                        status.text("正在生成周报...")
                    
                    # 更新响应内容
                    if resp.event == RunEvent.run_response and isinstance(resp.content, str):
                        response_content += resp.content
                        # 实时更新显示内容
                        with tab1:
                            response_placeholder.markdown(response_content)
                    
                    # 更新引用(如有)
                    if resp.citations and resp.citations.urls:
                        with tab2:
                            citations_html = "<ol>"
                            for citation in resp.citations.urls:
                                if citation.url:
                                    citations_html += f'<li><a href="{citation.url}" target="_blank">{citation.title or citation.url}</a></li>'
                            citations_html += "</ol>"
                            citations_placeholder.markdown(citations_html, unsafe_allow_html=True)
            
            # 完成进度
            progress.progress(100)
            status.success("✅ 学术周报生成完成!")
            
        except Exception as e:
            progress.progress(100)
            status.error(f"生成过程中发生错误: {str(e)}")