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

# Initialize position state variables if they don't exist
if 'cup_position' not in st.session_state:
    st.session_state.cup_position = {'x': -1, 'y': 0.7, 'z': 0}
if 'shelf_position' not in st.session_state:
    st.session_state.shelf_position = {'x': 1, 'y': 0.6, 'z': 0}

# Create two columns for the top section
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Object Positions")
    # Cup position inputs
    st.write("Cup Position")
    st.session_state.cup_position['x'] = st.number_input("Cup X", value=st.session_state.cup_position['x'])
    st.session_state.cup_position['y'] = st.number_input("Cup Y", value=st.session_state.cup_position['y'])
    st.session_state.cup_position['z'] = st.number_input("Cup Z", value=st.session_state.cup_position['z'])
    
    # Shelf position inputs
    st.write("Shelf Position")
    st.session_state.shelf_position['x'] = st.number_input("Shelf X", value=st.session_state.shelf_position['x'])
    st.session_state.shelf_position['y'] = st.number_input("Shelf Y", value=st.session_state.shelf_position['y'])
    st.session_state.shelf_position['z'] = st.number_input("Shelf Z", value=st.session_state.shelf_position['z'])

# Modified HTML code with position parameters
html_code = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Scene</title>
    <style>
        body {{ margin: 0; }}
        canvas {{ display: block; }}
    </style>
</head>
<body>
    <script type="module">
        import * as THREE from 'https://cdn.skypack.dev/three@0.128.0/build/three.module.js';
        import {{ OrbitControls }} from 'https://cdn.skypack.dev/three@0.128.0/examples/jsm/controls/OrbitControls.js';

        let scene, camera, renderer;

        function init() {{
            scene = new THREE.Scene();
            camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
            
            // 修改相机位置到右斜上方
            camera.position.set(2.5, 3.5, 6);
            camera.lookAt(0, 0, 0);

            renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            document.body.appendChild(renderer.domElement);

            const geometryTable = new THREE.BoxGeometry(5.0, 0.4, 5.0);
            const materialTable = new THREE.MeshBasicMaterial({{ color: 0x8B4513 }});
            const table = new THREE.Mesh(geometryTable, materialTable);
            scene.add(table);

            const geometryCup = new THREE.CylinderGeometry(0.5, 0.5, 1, 32);
            const materialCup = new THREE.MeshBasicMaterial({{ color: 0xFFD700 }});
            const cup = new THREE.Mesh(geometryCup, materialCup);
            cup.position.set({st.session_state.cup_position['x']}, 
                           {st.session_state.cup_position['y']}, 
                           {st.session_state.cup_position['z']});
            scene.add(cup);

            const geometryShelf = new THREE.BoxGeometry(2, 0.2, 3);
            const materialShelf = new THREE.MeshBasicMaterial({{ color: 0xA0522D }});
            const shelf = new THREE.Mesh(geometryShelf, materialShelf);
            shelf.position.set({st.session_state.shelf_position['x']}, 
                             {st.session_state.shelf_position['y']}, 
                             {st.session_state.shelf_position['z']});
            scene.add(shelf);

            const controls = new OrbitControls(camera, renderer.domElement);
            window.addEventListener('resize', onWindowResize, false);
            animate();
        }}

        function onWindowResize() {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }}

        function animate() {{
            requestAnimationFrame(animate);
            renderer.render(scene, camera);
        }}

        init();
    </script>
</body>
</html>
"""

with col2:
    # Add 3D visualization
    st.components.v1.html(html_code, height=600)

# Set your API key
YOUR_API_KEY = "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"
os.environ["PPLX_API_KEY"] = YOUR_API_KEY

# Initialize API client
client = openai.OpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")


if 'plan' not in st.session_state:
    st.session_state['plan'] = None

if 'workflow_graph' not in st.session_state:
    st.session_state['workflow_graph'] = None

if 'shared_tasks' not in st.session_state:
    st.session_state['shared_tasks'] = {}


# Function to generate structured plan
def generate_plan(user_input):
    prompt = f"""
        ### Agent Capability Description

        1. **Vision Recognition Agent**
        - **Role**: Responsible for identifying and classifying objects, determining their position, shape, and material.
        - **Capabilities**:
            - Capture images from the current camera.
            - Detect and recognize objects in the image, returning object categories and location information.
            - Classify materials based on object characteristics (e.g., metal, plastic, glass).
            - Obtain the pose information of objects in three-dimensional space.
        - **Task Scope**:
            - Confirm the existence of the target object before executing tasks and return relevant information.

        2. **Motion Planning Agent**
        - **Role**: Generate the motion path for the robotic arm based on vision recognition results.
        - **Capabilities**:
            - Plan a motion path from the starting position to the target position.
            - Consider obstacles during path planning, returning a path that avoids them.
            - Obtain information about the planned motion trajectory.
            - Execute the specified motion trajectory.
        - **Task Scope**:
            - Receive object position information from the vision recognition agent to generate a motion plan.

        3. **Grasping Strategy Agent**
        - **Role**: Choose an appropriate grasping strategy based on object type and grasping method.
        - **Capabilities**:
            - Select an appropriate gripper based on object type (e.g., mechanical claw, vacuum suction).
            - Calculate the required grasping force to safely grasp objects.
            - Execute grasping actions to pick up specified objects with the robotic arm.
        - **Task Scope**:
            - Select an appropriate grasping strategy based on information provided by the vision recognition agent.

        4. **Execution Control Agent**
        - **Role**: Control the actual execution process of the robotic arm, including grasping and moving.
        - **Capabilities**:
            - Move the robotic arm to a specified position.
            - Control the gripper to execute grasping actions.
            - Control the gripper to release objects.
            - Obtain the current status of the robotic arm (e.g., whether it is in motion, whether it successfully grasped an object).
        - **Task Scope**:
            - Receive instructions from both the motion planning agent and the grasping strategy agent to execute specific actions.

        5. **Feedback and Adjustment Agent**
        - **Role**: Monitor real-time feedback during execution and make adjustments as needed.
        - **Capabilities**:
            - Monitor the execution status of the robotic arm in real-time, checking for errors or deviations.
            - Adjust motion paths based on feedback to optimize execution effectiveness.
            - Record data during execution for subsequent analysis and optimization.
        - **Task Scope**:
            - Monitor status during execution and make adjustments as necessary.

        Please generate a structured plan based on the following user input, formatted as pure JSON without adding any other text:
        
        User Input: "{user_input}"
        
        Output Format:
        {{
            "tasks": [
                {{"id": "task1", "description": "Capture images of the target object and perform recognition", "assigned_agent": "Vision Recognition Agent", "depends_on": []}},
                {{"id": "task2", "description": "Generate a motion path to move to the target position", "assigned_agent": "Motion Planning Agent", "depends_on": ["task1"]}},
                {{"id": "task3", "description": "Select an appropriate grasping strategy and calculate grasping force", "assigned_agent": "Grasping Strategy Agent", "depends_on": ["task1"]}},
                {{"id": "task4", "description": "Control the robotic arm to move and execute grasping actions", "assigned_agent": "Execution Control Agent", "depends_on": ["task2", "task3"]}},
                {{"id": "task5", "description": "Monitor execution process and make necessary adjustments", "assigned_agent": "Feedback and Adjustment Agent", "depends_on": ["task4"]}}
            ]
        }}
        
        Please ensure that each sub-task includes an appropriate agent name for routing to the designated agent later.
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
                    "curveness": 0.3  # Add curve to better show direction
                },
                "symbol": ["none", "arrow"],  # Add arrow at the end of the line
                "symbolSize": [5, 10]  # Size of the arrow
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
            edge_length=[50, 200],  # Control edge length range
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

# Function to navigate to agent page based on agent type
def navigate_to_agent(agent_name):
    st.session_state['selected_agent'] = agent_name
    # Filter tasks for the selected agent
    if st.session_state['plan']:
        assigned_tasks = [task for task in st.session_state['plan']['tasks'] 
                        if task['assigned_agent'] == agent_name]
        st.session_state['shared_tasks'][agent_name] = assigned_tasks

    try:
        # 使用相对于主应用的路径
        base_path = "pages"
        if agent_name == "Vision Recognition Agent":
            st.switch_page(f"{base_path}/eye_agent.py")
        elif agent_name == "Motion Planning Agent":
            st.switch_page(f"{base_path}/move_agent.py")  
        elif agent_name == "Grasping Strategy Agent":
            st.switch_page(f"{base_path}/hand_agent.py")
        elif agent_name == "Execution Control Agent":
            st.switch_page(f"{base_path}/excute_agent.py")
        elif agent_name == "Feedback and Adjustment Agent":
            st.switch_page(f"{base_path}/adjust_agent.py")
        else:
            st.write("No detailed information available for this agent.")
    except Exception as e:
        st.error(f"Error navigating to agent page: {str(e)}")
        st.write(f"Current working directory: {os.getcwd()}")

# Streamlit application part
st.title("AI Assistant for Task Planning and Execution")

user_input = st.text_input("Enter your task description:")

if st.button("Generate Plan"):
    if user_input:
        plan = generate_plan(user_input)
        
        if plan:
            st.session_state['plan'] = plan  # Save to session state
            
            # Update shared_tasks by categorizing tasks for each agent
            agent_tasks = {}
            for task in plan['tasks']:
                agent_name = task['assigned_agent']
                if agent_name not in agent_tasks:
                    agent_tasks[agent_name] = []
                agent_tasks[agent_name].append(task)
            
            st.session_state['shared_tasks'] = agent_tasks
            
            nodes, links = build_graph(plan)
            graph = visualize_graph(nodes, links)
            st.session_state['workflow_graph'] = graph  # Save graph            
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.write("Generated Plan:")
                st.json(plan)
                    
            with col2:
                st_pyecharts(graph)
            
            
            # Update cup position after graph generation
            st.session_state.cup_position = {'x': 1, 'y': 1.1, 'z': 0}
            # Trigger page rerun to update 3D visualization
            st.rerun()

# Restore previous state if exists
elif st.session_state['plan'] and st.session_state['workflow_graph']:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("Generated Plan:")
        st.json(st.session_state['plan'])
            
    with col2:
        st_pyecharts(st.session_state['workflow_graph'])