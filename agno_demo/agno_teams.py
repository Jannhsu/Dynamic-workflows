from textwrap import dedent

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.yfinance import YFinanceTools
from agno.models.openai import OpenAIChat
import os

os.environ["OPENAI_API_KEY"] = "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"
os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"

web_agent = Agent(
    name="Web Search Agent",
    role="Handle web search requests",
    model=OpenAIChat(
        id="openai/gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],  # 显式传递 API Key
        base_url=os.environ["OPENAI_API_BASE"],  # 显式指定 base_url
        default_headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},  # 添加 Authorization 请求头
    ),
    tools=[DuckDuckGoTools()],
    instructions="Always include sources.",
    add_datetime_to_instructions=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Handle financial data requests",
    model=OpenAIChat(
        id="openai/gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],  # 显式传递 API Key
        base_url=os.environ["OPENAI_API_BASE"],  # 显式指定 base_url
        default_headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},  # 添加 Authorization 请求头
    ),
    tools=[
        YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)
    ],
    instructions="Use tables to display data.",
    add_datetime_to_instructions=True,
)

team_leader = Team(
    name="Reasoning Finance Team Leader",
    mode="coordinate",
    model=OpenAIChat(
        id="openai/gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],  # 显式传递 API Key
        base_url=os.environ["OPENAI_API_BASE"],  # 显式指定 base_url
        default_headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},  # 添加 Authorization 请求头
    ),
    members=[web_agent, finance_agent],
    tools=[ReasoningTools(add_instructions=True)],
    instructions=[
        "Use tables to display data.",
        "Only respond with the final answer, no other text.",
    ],
    markdown=True,
    show_members_responses=True,
    enable_agentic_context=True,
    add_datetime_to_instructions=True,
    success_criteria="The team has successfully completed the task.",
)

task = """\
Analyze the semiconductor market performance focusing on:
- NVIDIA (NVDA)
- AMD (AMD)
- Intel (INTC)
- Taiwan Semiconductor (TSM)
Compare their market positions, growth metrics, and future outlook."""

team_leader.print_response(
    task,
    stream=True,
    stream_intermediate_steps=True,
    show_full_reasoning=True,
)