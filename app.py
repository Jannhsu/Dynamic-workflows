import streamlit as st
import openai
import json
import re
import os
from pyecharts import options as opts
from pyecharts.charts import Graph
from streamlit_echarts import st_pyecharts

# Set the page to wide mode
st.set_page_config(layout="wide")

# Set your API key
YOUR_API_KEY = "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"
os.environ["PPLX_API_KEY"] = YOUR_API_KEY

# Initialize API client
client = openai.OpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")

# Function to generate structured plan
def generate_plan(user_input):
    prompt = f"""
        ### 代理能力描述

        1. **视觉识别代理**
        - **角色**：负责识别和分类物体，确定其位置、形状和材质。
        - **能力**：
            - 获取当前摄像头图像。
            - 检测并识别图像中的物体，返回物体类别和位置信息。
            - 根据物体特征分类其材质（如金属、塑料、玻璃等）。
            - 获取物体在三维空间中的姿态信息。
        - **任务范围**：
            - 在执行任务前确认目标物体是否存在，并返回相关信息。

        2. **运动规划代理**
        - **角色**：根据视觉识别结果生成机械臂的运动路径。
        - **能力**：
            - 规划从起始位置到目标位置的运动路径。
            - 在路径规划中考虑障碍物，返回避障后的路径。
            - 获取规划好的运动轨迹信息。
            - 执行指定的运动轨迹。
        - **任务范围**：
            - 接收来自视觉识别代理的物体位置信息，生成运动计划。

        3. **抓取策略代理**
        - **角色**：根据物体类型和抓取方式选择合适的抓取策略。
        - **能力**：
            - 根据物体类型选择合适的抓取器（如机械夹爪、真空吸附器等）。
            - 计算所需的抓取力以安全抓取物体。
            - 执行抓取动作，将指定物体抓取到机械臂上。
        - **任务范围**：
            - 根据视觉识别代理提供的信息选择合适的抓取策略。

        4. **执行控制代理**
        - **角色**：控制机械臂的实际执行过程，包括抓取和移动。
        - **能力**：
            - 将机械臂移动到指定位置。
            - 控制抓取器执行抓取动作。
            - 控制抓取器释放物体。
            - 获取机械臂当前状态（如是否在运动、是否成功抓取等）。
        - **任务范围**：
            - 接收来自运动规划代理和抓取策略代理的指令，执行具体动作。

        5. **反馈与调整代理**
        - **角色**：监控执行过程中的实时反馈，并根据需要进行调整。
        - **能力**：
            - 实时监控机械臂执行状态，检查是否发生错误或偏差。
            - 根据反馈调整运动路径以优化执行效果。
            - 记录执行过程中的数据以便后续分析和优化。
        - **任务范围**：
            - 在执行过程中监控状态，并根据需要进行调整。

        请根据以下用户输入生成一个结构化计划，格式为纯 JSON，不要添加任何其他文本：
        
        用户输入: "{user_input}"
        
        输出格式:
        {{
            "tasks": [
                {{"id": "task1", "description": "获取目标物体图像并进行识别", "assigned_agent": "视觉识别代理", "depends_on": []}},
                {{"id": "task2", "description": "生成运动路径以移动到目标位置", "assigned_agent": "运动规划代理", "depends_on": ["task1"]}},
                {{"id": "task3", "description": "选择合适的抓取策略并计算抓取力", "assigned_agent": "抓取策略代理", "depends_on": ["task1"]}},
                {{"id": "task4", "description": "控制机械臂移动并执行抓取动作", "assigned_agent": "执行控制代理", "depends_on": ["task2", "task3"]}},
                {{"id": "task5", "description": "监控执行过程并进行必要调整", "assigned_agent": "反馈与调整代理", "depends_on": ["task4"]}}
            ]
        }}
        
        请确保在每个子任务中包含合适的代理名称，以便于后续路由到指定的代理。
    """
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are an artificial intelligence assistant and you need to "
                "generate a structured plan based on user input."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]
    
    response = client.chat.completions.create(
        model="llama-3.1-sonar-large-128k-online",
        messages=messages,
    )
    
    json_content = response.choices[0].message.content
    json_match = re.search(r'\{.*\}', json_content, re.DOTALL)

    if json_match:
        json_str = json_match.group(0)
        return json.loads(json_str)
    
    return None

# Build graph structure and return nodes and links
def build_graph(plan):
    nodes = []
    links = []

    for task in plan["tasks"]:
        nodes.append({"name": task["id"], "value": task["description"]})
        
        for dep in task["depends_on"]:
            links.append({"source": dep, "target": task["id"]})

    return nodes, links

# Visualize workflow graph structure
def visualize_graph(nodes, links):
    graph = (
        Graph()
        .add("", nodes, links, repulsion=8000)
        .set_global_opts(title_opts=opts.TitleOpts(title="Workflow Graph"))
    )
    
    return graph

# Streamlit application part
st.title("StreamLit 🤝 LangGraph")
st.subheader("Simple Chat Streaming with Workflow Visualization")

user_input = st.text_input("Enter your task description:")

if st.button("Generate Plan"):
    if user_input:
        plan = generate_plan(user_input)
        
        if plan:
            nodes, links = build_graph(plan)
            
            # Use Streamlit's column layout to display the plan and visualization results
            col1, col2 = st.columns([1, 2])  # Adjust column widths
            
            with col1:
                st.write("Generated Plan:")
                st.json(plan)
            
            with col2:
                graph = visualize_graph(nodes, links)
                st_pyecharts(graph)