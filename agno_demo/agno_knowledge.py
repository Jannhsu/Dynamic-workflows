'''import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
from agno.tools.yfinance import YFinanceTools

os.environ["OPENAI_API_KEY"] = "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"
os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"

agent = Agent(
    model=OpenAIChat(
        id="openai/gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],  # 显式传递 API Key
        base_url=os.environ["OPENAI_API_BASE"],  # 显式指定 base_url
        default_headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},  # 添加 Authorization 请求头
    ),
    tools=[
        ReasoningTools(add_instructions=True),
        YFinanceTools(
            stock_price=True,
            analyst_recommendations=True,
            company_info=True,
            company_news=True,
        ),
    ],
    show_tool_calls=True,
    instructions=[
        "Use tables to display data",
        "Only output the report, no other text",
    ],
    markdown=True,
)

agent.print_response(
    "Write a report on NVDA",
    stream=True,
    show_full_reasoning=True,
    stream_intermediate_steps=True,
)'''


from agno.agent import Agent
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.url import UrlKnowledge
from agno.tools.reasoning import ReasoningTools
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.models.openai import OpenAIChat
import os

os.environ["OPENAI_API_KEY"] = "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"
os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"

# Load Agno documentation in a knowledge base
knowledge = UrlKnowledge(
    urls=["https://docs.agno.com/introduction/agents.md"],
    vector_db=LanceDb(
        uri="tmp/lancedb",
        table_name="agno_docs",
        search_type=SearchType.hybrid,
        # Use OpenAI for embeddings
        embedder=OpenAIEmbedder(id="text-embedding-v3",
        api_key="sk-c6e96354ac2a4a28bc2bf10eb115212f",  # 显式传递 API Key
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 显式指定 base_url
        dimensions=1024),
    ),
)

agent = Agent(
    name="Agno Assist",
    model=OpenAIChat(
        id="openai/gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],  # 显式传递 API Key
        base_url=os.environ["OPENAI_API_BASE"],  # 显式指定 base_url
        default_headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},  # 添加 Authorization 请求头
    ),
    instructions=[
        "Use tables to display data.",
        "Include sources in your response.",
        "Search your knowledge before answering the question.",
        "Only include the output in your response. No other text.",
    ],
    knowledge=knowledge,
    tools=[ReasoningTools(add_instructions=True)],
    add_datetime_to_instructions=True,
    markdown=True,
)

if __name__ == "__main__":
    # Load the knowledge base, comment out after first run
    # Set recreate to True to recreate the knowledge base if needed
    agent.knowledge.load(recreate=False)
    agent.print_response(
        "What are Agents?",
        stream=True,
        show_full_reasoning=True,
        stream_intermediate_steps=True,
    )