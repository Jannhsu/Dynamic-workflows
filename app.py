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


if 'plan' not in st.session_state:
    st.session_state['plan'] = None

if 'workflow_graph' not in st.session_state:
    st.session_state['workflow_graph'] = None

if 'shared_tasks' not in st.session_state:
    st.session_state['shared_tasks'] = {}


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
            - 执行抓取动作，���指定物体抓取到机械臂上。
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
        
        输出格��:
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
        if agent_name == "视觉识别代理":
            st.switch_page(f"{base_path}/eye_agent.py")
        elif agent_name == "运动规划代理":
            st.switch_page(f"{base_path}/move_agent.py")  
        elif agent_name == "抓取策略代理":
            st.switch_page(f"{base_path}/hand_agent.py")
        elif agent_name == "执行控制代理":
            st.switch_page(f"{base_path}/excute_agent.py")
        elif agent_name == "反馈与调整代理":
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

# Restore previous state if exists
elif st.session_state['plan'] and st.session_state['workflow_graph']:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("Generated Plan:")
        st.json(st.session_state['plan'])
            
    with col2:
        st_pyecharts(st.session_state['workflow_graph'])
