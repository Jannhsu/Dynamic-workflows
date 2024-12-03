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

st.title("Motion Planning Agent")

# Function to generate structured plan for visual tasks
def generate_visual_plan(user_input):
    prompt = f"""
        ### API 描述

        1. **规划路径 API**
        - **名称**：PlanPath
        - **参数**：
            - `start_position`: 机械臂的起始位置坐标。
            - `target_position`: 目标位置的坐标。

        2. **避障路径 API**
        - **名称**：AvoidObstacles
        - **参数**：
            - `path`: 初步规划的运动路径。

        3. **获取轨迹 API**
        - **名称**：GetTrajectory
        - **参数**：无

        4. **执行运动 API**
        - **名称**：ExecuteMovement
        - **参数**：
            - `trajectory`: 规划好的运动轨迹信息。

        请根据以下用户输入生成一个结构化计划，格式为纯 JSON，不要添加任何其他文本：
        
        用户输入: "{user_input}"
        
        输出格式:
        {{
            "tasks": [
                {{"id": "task1", "description": "规划从起始位置到目标位置的运动路径", "api_name": "PlanPath", "api_params": {{"start_position": "起始坐标", "target_position": "目标坐标"}}, "depends_on": []}},
                {{"id": "task2", "description": "在路径规划中考虑障碍物并返回避障后的路径", "api_name": "AvoidObstacles", "api_params": {{"path": "初步路径"}}, "depends_on": ["task1"]}},
                {{"id": "task3", "description": "获取规划好的运动轨迹信息", "api_name": "GetTrajectory", "api_params": {{}}, "depends_on": ["task2"]}},
                {{"id": "task4", "description": "执行指定的运动轨迹", "api_name": "ExecuteMovement", "api_params": {{"trajectory": "轨迹信息"}}, "depends_on": ["task3"]}}
            ]
        }}
        
        请确保在每个子任务中包含要调用的API名称和相应的参数，以便于后续调用。
    """
    
    messages = [
        {"role": "system", "content": "You are an AI assistant for motion planning tasks."},
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
        nodes.append({
            "name": task["id"], 
            "value": task["description"],
            "symbol": "circle",
            "symbolSize": 50,
            "label": {"show": True}
        })
        
        for dep in task["depends_on"]:
            links.append({
                "source": dep, 
                "target": task["id"],
                "lineStyle": {
                    "type": "solid",
                    "curveness": 0.3
                },
                "symbol": ["none", "arrow"],
                "symbolSize": [5, 10]
            })

    return nodes, links

def visualize_graph(nodes, links):
    graph = (
        Graph(init_opts=opts.InitOpts(width="1500px", height="1500px"))
        .add(
            "",
            nodes,
            links,
            repulsion=4000,
            edge_length=[50, 200],
            layout="force",
            is_roam=True,
            is_draggable=True,
            linestyle_opts=opts.LineStyleOpts(
                width=2,
                opacity=0.9,
                curve=0.3
            ),
            label_opts=opts.LabelOpts(
                position="inside",
                font_size=12,
                font_weight="bold"
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="Workflow Graph"),
            legend_opts=opts.LegendOpts(is_show=False)
        )
    )
    
    return graph

# Back button at the top
if st.button("Back to Main Page"):
    try:
        st.switch_page("app.py")
    except Exception as e:
        st.error(f"Error returning to main page: {str(e)}")

# Main interface
agent_name = "运动规划代理"
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
                st.write("Generated Motion Planning Plan:")
                st.json(plan)
                
                with right_col:
                    nodes, links = build_graph(plan)
                    graph = visualize_graph(nodes, links)
                    st_pyecharts(graph)
            else:
                status_placeholder.error("Task execution failed!")

else:
    st.warning("No tasks assigned to Motion Planning Agent")
    user_input = st.text_input("Enter manual task:", "")
    
    if st.button("Execute Manual Task") and user_input:
        left_col, right_col = st.columns([1, 1.5])
        
        plan = generate_visual_plan(user_input)
        if plan:
            with left_col:
                st.write("Generated Motion Planning Plan:")
                st.json(plan)
            
            with right_col:
                nodes, links = build_graph(plan)
                graph = visualize_graph(nodes, links)
                st_pyecharts(graph)
