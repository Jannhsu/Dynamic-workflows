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

st.title("Hand manipulation Agent")

# Function to generate structured plan for visual tasks
def generate_visual_plan(user_input):
    prompt = f"""
        ### API Description

        1. **Select Gripper API**
        - **Name**: select_gripper
        - **Parameters**:
            - `object`: Information about the object to be grasped, including its type, shape, and material.

        2. **Calculate Grasping Force API**
        - **Name**: calculate_grasping_force
        - **Parameters**:
            - `object`: Information about the object to be grasped, including its weight and material characteristics.

        3. **Execute Grasping Action API**
        - **Name**: execute_grasp_action
        - **Parameters**:
            - `gripper`: The type of gripper to be used.
            - `object`: Information about the object to be grasped.

        Please generate a structured plan based on the following user input, formatted as pure JSON without adding any other text:
        
        User Input: "{user_input}"
        
        Output Format:
        {{
            "tasks": [
                {{"id": "task1", "description": "Select an appropriate gripper to grasp the object", "api_name": "select_gripper", "api_params": {{"object": "object_information"}}, "depends_on": []}},
                {{"id": "task2", "description": "Calculate the required grasping force to safely grasp the object", "api_name": "calculate_grasping_force", "api_params": {{"object": "object_information"}}, "depends_on": ["task1"]}},
                {{"id": "task3", "description": "Execute the grasping action to pick up the object with the robotic arm", "api_name": "execute_grasp_action", "api_params": {{"gripper": "selected_gripper_type", "object": "object_information"}}, "depends_on": ["task2"]}}
            ]
        }}
        
        Please ensure that each sub-task includes the API name to be called and the corresponding parameters for subsequent invocation.
    """
    
    messages = [
        {"role": "system", "content": "You are an AI assistant for hand manipulation tasks."},
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
agent_name = "Grasping Strategy Agent"
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
                st.write("Generated Hand Manipulation Plan:")
                st.json(plan)
                
                with right_col:
                    nodes, links = build_graph(plan)
                    graph = visualize_graph(nodes, links)
                    st_pyecharts(graph)
            else:
                status_placeholder.error("Task execution failed!")

else:
    st.warning("No tasks assigned to Hand Manipulation Agent")
    user_input = st.text_input("Enter manual task:", "")
    
    if st.button("Execute Manual Task") and user_input:
        left_col, right_col = st.columns([1, 1.5])
        
        plan = generate_visual_plan(user_input)
        if plan:
            with left_col:
                st.write("Generated Hand Manipulation Plan:")
                st.json(plan)
            
            with right_col:
                nodes, links = build_graph(plan)
                graph = visualize_graph(nodes, links)
                st_pyecharts(graph)
