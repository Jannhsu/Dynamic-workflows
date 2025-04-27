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
        ### API Description

        1. **Move Arm to Specified Position API**
        - **Name**: move_arm_to_position
        - **Parameters**:
            - `position`: The coordinates of the target position.

        2. **Grip Object API**
        - **Name**: grip_object
        - **Parameters**:
            - `gripper`: The type of gripper used (e.g., claw, suction cup).

        3. **Release Object API**
        - **Name**: release_object
        - **Parameters**:
            - `gripper`: The type of gripper used to release the object.

        4. **Get Arm Status API**
        - **Name**: get_status
        - **Parameters**: None

        Please generate a structured plan based on the following user input, formatted as pure JSON without adding any other text:
        
        User Input: "{user_input}"
        
        Output Format:
        {{
            "tasks": [
                {{"id": "task1", "description": "Move the arm to the target position", "api_name": "move_arm_to_position", "api_params": {{"position": "coordinates"}}, "depends_on": []}},
                {{"id": "task2", "description": "Use the claw to grip the object", "api_name": "grip_object", "api_params": {{"gripper": "claw"}}, "depends_on": ["task1"]}},
                {{"id": "task3", "description": "Release the gripped object", "api_name": "release_object", "api_params": {{"gripper": "claw"}}, "depends_on": ["task2"]}},
                {{"id": "task4", "description": "Get the current status of the arm", "api_name": "get_status", "api_params": {{}}, "depends_on": ["task3"]}}
            ]
        }}
        
        Please ensure that each sub-task includes the name of the API to be called and the corresponding parameters for subsequent calls.
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
agent_name = "Execution Control Agent"
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
