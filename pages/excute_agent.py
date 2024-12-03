import streamlit as st
from pathlib import Path
import sys
import openai
import json
import re
import os
from pyecharts import options as opts
from pyecharts.charts import Graph
from streamlit_echarts import st_pyecharts

# Set your API key
YOUR_API_KEY = "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"
os.environ["PPLX_API_KEY"] = YOUR_API_KEY

# Initialize API client
client = openai.OpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(layout="wide")

st.title("Execute Control Agent")

# Function to generate structured plan for visual tasks
def generate_visual_plan(user_input):
    prompt = f"""
        ### API 描述

        1. **移动机械臂到指定位置 API**
        - **名称**：MoveArmToPosition
        - **参数**：
            - `position`: 目标位置的坐标。

        2. **抓取物体 API**
        - **名称**：GripObject
        - **参数**：
            - `gripper`: 使用的抓手类型（如夹爪、吸盘等）。

        3. **释放物体 API**
        - **名称**：ReleaseObject
        - **参数**：
            - `gripper`: 控制抓取器释放物体的类型。

        4. **获取机械臂状态 API**
        - **名称**：GetStatus
        - **参数**：无

        请根据以下用户输入生成一个结构化计划，格式为纯 JSON，不要添加任何其他文本：
        
        用户输入: "{user_input}"
        
        输出格式:
        {{
            "tasks": [
                {{"id": "task1", "description": "将机械臂移动到目标位置", "api_name": "MoveArmToPosition", "api_params": {{"position": "坐标"}},"depends_on": []}},
                {{"id": "task2", "description": "使用夹爪抓取物体", "api_name": "GripObject", "api_params": {{"gripper": "夹爪"}}, "depends_on": ["task1"]}},
                {{"id": "task3", "description": "释放抓取的物体", "api_name": "ReleaseObject", "api_params": {{"gripper": "夹爪"}}, "depends_on": ["task2"]}},
                {{"id": "task4", "description": "获取机械臂当前状态", "api_name": "GetStatus", "api_params": {{}}, "depends_on": ["task3"]}}
            ]
        }}
        
        请确保在每个子任务中包含要调用的API名称和相应的参数，以便于后续调用。
    """
    
    messages = [
        {"role": "system", "content": "You are an AI assistant for executing control tasks."},
        {"role": "user", "content": prompt},
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


# Back button at the top
if st.button("Back to Main Page"):
    try:
        st.switch_page("app.py")
    except Exception as e:
        st.error(f"Error returning to main page: {str(e)}")

# Main interface
agent_name = "执行控制代理"
assigned_tasks = st.session_state.get('shared_tasks', {}).get(agent_name, [])

# Display assigned tasks
if assigned_tasks:
    st.write("📋 Assigned Tasks:")
    for task in assigned_tasks:
        st.info(f"Task ID: {task['id']}\nDescription: {task['description']}")
    
    default_input = assigned_tasks[0]['description']
    
    # Create main left-right layout
    left_col, right_col = st.columns([1, 1.5])
    
    with left_col:
        st.write("Task Status:")
        status_placeholder = st.empty()
        
        if st.button("Execute Task"):
            status_placeholder.info("Executing task...")
            plan = generate_visual_plan(default_input)
            
            if plan:
                status_placeholder.success("Task completed!")
                st.write("Generated Execute Control Plan:")
                st.json(plan)
                
                with right_col:
                    nodes, links = build_graph(plan)
                    graph = visualize_graph(nodes, links)
                    st_pyecharts(graph)
            else:
                status_placeholder.error("Task execution failed!")

else:
    st.warning("No tasks assigned to Execute Control Agent")
    user_input = st.text_input("Enter manual task:", "")
    
    if st.button("Execute Manual Task") and user_input:
        left_col, right_col = st.columns([1, 1.5])
        
        plan = generate_visual_plan(user_input)
        if plan:
            with left_col:
                st.write("Generated Execute Control Plan:")
                st.json(plan)
            
            with right_col:
                nodes, links = build_graph(plan)
                graph = visualize_graph(nodes, links)
                st_pyecharts(graph)
