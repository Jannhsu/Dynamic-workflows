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

st.title("Feedback and Adjustment Agent")

# Function to generate structured plan for visual tasks
def generate_visual_plan(user_input):
    prompt = f"""
        ### API Description

        1. **Monitor Execution Status API**
        - **Name**: monitor_execution_status
        - **Parameters**:
            - `execution_id`: The ID of the current executing task.
            - `timeout`: Monitoring timeout duration (in seconds).

        2. **Adjust Path API**
        - **Name**: adjust_path
        - **Parameters**:
            - `trajectory`: Detailed information about the current motion trajectory.
            - `adjustment_factor`: The factor for adjusting the path (e.g., offset or angle).

        3. **Log Data API**
        - **Name**: log_data
        - **Parameters**:
            - `log_entry`: The content of the log entry to be recorded.
            - `timestamp`: The timestamp for the log entry.

        Please generate a structured plan based on the following user input, formatted as pure JSON without adding any other text:
        
        User Input: "{user_input}"
        
        Output Format:
        {{
            "tasks": [
                {{"id": "task1", "description": "Real-time monitoring of the robotic arm's execution status", "api_name": "monitor_execution_status", "api_params": {{"execution_id": "current_task_id", "timeout": 30}}, "depends_on": []}},
                {{"id": "task2", "description": "Adjust motion path based on feedback", "api_name": "adjust_path", "api_params": {{"trajectory": "current_trajectory", "adjustment_factor": 0.1}}, "depends_on": ["task1"]}},
                {{"id": "task3", "description": "Log data during the execution process", "api_name": "log_data", "api_params": {{"log_entry": "Execution status normal", "timestamp": "current_time"}}, "depends_on": ["task1"]}}
            ]
        }}
        
        Please ensure that each sub-task includes the API name to be called and the corresponding parameters for subsequent calls.
    """
    
    messages = [
        {"role": "system", "content": "You are an AI assistant for feedback and adjustment tasks."},
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
agent_name = "Feedback and Adjustment Agent"
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
                st.write("Generated Feedback and Adjustment Plan:")
                st.json(plan)
                
                with right_col:
                    nodes, links = build_graph(plan)
                    graph = visualize_graph(nodes, links)
                    st_pyecharts(graph)
            else:
                status_placeholder.error("Task execution failed!")

else:
    st.warning("No tasks assigned to Feedback and Adjustment Agent")
    user_input = st.text_input("Enter manual task:", "")
    
    if st.button("Execute Manual Task") and user_input:
        left_col, right_col = st.columns([1, 1.5])
        
        plan = generate_visual_plan(user_input)
        if plan:
            with left_col:
                st.write("Generated Feedback and Adjustment Plan:")
                st.json(plan)
            
            with right_col:
                nodes, links = build_graph(plan)
                graph = visualize_graph(nodes, links)
                st_pyecharts(graph)
