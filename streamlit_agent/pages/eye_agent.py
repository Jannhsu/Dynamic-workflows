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

st.title("Visual Recognition Agent")

# Function to generate structured plan for visual tasks
def generate_visual_plan(user_input):
    prompt = f"""
        ### API Description

        1. **Get Current Camera Image API**
        - **Name**: get_current_camera_image
        - **Parameters**: None

        2. **Detect Objects API**
        - **Name**: detect_objects
        - **Parameters**:
            - `image`: The image data to be processed.

        3. **Classify Material API**
        - **Name**: classify_material
        - **Parameters**:
            - `object`: The information of the object to be classified.

        4. **Get Object Pose API**
        - **Name**: get_object_pose
        - **Parameters**:
            - `object`: The information of the object for which to obtain pose data.

        Please generate a structured plan based on the following user input, formatted as pure JSON without adding any other text:
        
        User Input: "{user_input}"
        
        Output Format:
        {{
            "tasks": [
                {{"id": "task1", "description": "Get current camera image", "api_name": "get_current_camera_image", "api_params": {{}}, "depends_on": []}},
                {{"id": "task2", "description": "Detect objects in the image", "api_name": "detect_objects", "api_params": {{"image": "task1_result"}}, "depends_on": ["task1"]}},
                {{"id": "task3", "description": "Classify the material of detected objects", "api_name": "classify_material", "api_params": {{"object": "task2_result"}}, "depends_on": ["task2"]}},
                {{"id": "task4", "description": "Get pose information of detected objects", "api_name": "get_object_pose", "api_params": {{"object": "task2_result"}}, "depends_on": ["task2"]}}
            ]
        }}
    """
    
    messages = [
        {"role": "system", "content": "You are an AI assistant for visual recognition tasks."},
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

# Visualize workflow graph structure
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
agent_name = "Vision Recognition Agent"
assigned_tasks = st.session_state.get('shared_tasks', {}).get(agent_name, [])

# Display assigned tasks
if assigned_tasks:
    st.write("📋 Assigned Tasks:")
    for task in assigned_tasks:
        st.info(f"Task ID: {task['id']}\nDescription: {task['description']}")
    
    default_input = assigned_tasks[0]['description']
    
    # Create main left-right layout
    left_col, right_col = st.columns([1, 1.5])  # Adjust ratio for visualization
    
    with left_col:
        st.write("Task Status:")
        status_placeholder = st.empty()
        
        if st.button("Execute Task"):
            status_placeholder.info("Executing task...")
            plan = generate_visual_plan(default_input)
            
            if plan:
                status_placeholder.success("Task completed!")
                st.write("Generated Visual Recognition Plan:")
                st.json(plan)
                
                # Update visualization in right column
                with right_col:
                    nodes, links = build_graph(plan)
                    graph = visualize_graph(nodes, links)
                    st_pyecharts(graph)
            else:
                status_placeholder.error("Task execution failed!")

else:
    st.warning("No tasks assigned to Visual Recognition Agent")
    user_input = st.text_input("Enter manual task:", "")
    
    if st.button("Execute Manual Task") and user_input:
        # Create main left-right layout
        left_col, right_col = st.columns([1, 1.5])  # Adjust ratio for visualization
        
        plan = generate_visual_plan(user_input)
        if plan:
            with left_col:
                st.write("Generated Visual Recognition Plan:")
                st.json(plan)
            
            with right_col:
                nodes, links = build_graph(plan)
                graph = visualize_graph(nodes, links)
                st_pyecharts(graph)
