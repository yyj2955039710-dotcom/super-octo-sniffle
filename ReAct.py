import re
import json
import os
from llm_client import HelloAgentsLLM
from tools import ToolExecutor, search

# Windows控制台编码修复
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

REACT_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下：
{tools}

你必须严格按照以下格式进行回复（每行一个字段）：

Thought: 你的思考过程
Action: 工具名[参数]  或  Finish[最终答案]

示例：
Thought: 我需要搜索华为最新手机的信息
Action: Search[华为最新手机2024]
...

现在开始解决问题：
Question: {question}
History: {history}
"""

class ReActAgent:
    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []

    def run(self, question: str):
        self.history = []
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history) if self.history else "(无)"
            prompt = REACT_PROMPT_TEMPLATE.format(tools=tools_desc, question=question, history=history_str)

            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)
            if not response_text:
                print("错误：LLM未能返回有效响应。"); break

            print(f"LLM原始输出:\n{response_text}\n")

            thought, action = self._parse_output(response_text)
            if thought: print(f"思考: {thought}")
            if not action:
                print("警告：未能解析出有效的Action，流程终止。"); break

            # 检查是否是Finish指令
            finish_match = re.match(r"Finish\[(.*)\]", action.strip(), re.DOTALL)
            if finish_match:
                finish_content = finish_match.group(1).strip()
                # 如果是占位符，则返回完整的LLM输出作为答案
                if "已通过搜索获得答案" in finish_content:
                    final_answer = response_text.strip()
                else:
                    final_answer = finish_content
                print(f"最终答案: {final_answer[:200]}...")
                return final_answer

            # 解析工具调用
            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                self.history.append(f"Action: {action}")
                self.history.append("Observation: 无效的Action格式，请使用 工具名[参数] 格式。")
                continue

            print(f"行动: {tool_name}[{tool_input}]")
            tool_function = self.tool_executor.getTool(tool_name)
            observation = tool_function(tool_input) if tool_function else f"错误：未找到名为 '{tool_name}' 的工具。"

            print(f"观察: {observation}")
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        print("已达到最大步数，流程终止。")
        return None

    def _parse_output(self, text: str):
        """解析LLM输出，提取Thought和Action"""
        # 清理文本，移除可能的markdown代码块
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)

        # 尝试解析JSON格式的输出
        json_match = re.search(r'\{[^{}]*"cmd"\s*:\s*\[[^{}\]]+\][^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group()
                data = json.loads(json_str)
                if "cmd" in data and isinstance(data["cmd"], list):
                    cmd = data["cmd"]
                    if len(cmd) >= 2:
                        tool = cmd[0]
                        query = cmd[1]
                        return None, f"{tool}[{query}]"
                    elif len(cmd) == 1:
                        return None, f"Finish[{cmd[0]}]"
            except:
                pass

        # 尝试解析 {"cmd": ["Search", "query"]} 格式
        cmd_match = re.search(r'"cmd"\s*:\s*\["(\w+)"\s*,\s*"([^"]+)"\]', text)
        if cmd_match:
            tool_name = cmd_match.group(1)
            tool_input = cmd_match.group(2)
            return None, f"{tool_name}[{tool_input}]"

        # 标准格式: Thought: xxx\nAction: xxx
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None

        # 如果没有Thought，尝试从整个文本中找Action
        if not action:
            # 尝试匹配 工具名[参数] 格式
            action_match = re.search(r"(Search|WebSearch|Browse|Finish)\[([^\]]+)\]", text)
            if action_match:
                action = f"{action_match.group(1)}[{action_match.group(2)}]"

        # 如果仍然没有action，检查文本是否已经是答案（包含**标题或数字列表）
        if not action:
            lines = text.strip().split('\n')
            answer_lines = [l for l in lines if l.strip() and (l.strip().startswith('**') or re.match(r'^\d+\.', l.strip()) or l.strip().startswith('- '))]
            if len(answer_lines) >= 2:
                # 认为这是直接给出的答案，不是需要进一步处理的格式
                action = "Finish[已通过搜索获得答案]"

        return thought, action

        return thought, action

    def _parse_action(self, action_text: str):
        """解析 Action: 工具名[参数] 格式"""
        # 处理可能的引号
        action_text = action_text.strip().strip('`').strip()
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None

if __name__ == '__main__':
    llm = HelloAgentsLLM()
    tool_executor = ToolExecutor()
    search_desc = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    tool_executor.registerTool("Search", search_desc, search)
    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)

    print("=" * 50)
    print("ReAct 智能体已启动，输入问题开始对话（退出输入 q）")
    print("=" * 50)

    while True:
        question = input("\n你: ").strip()
        if question.lower() in ['q', '退出', 'exit']:
            print("再见！")
            break
        if not question:
            continue
        print()
        agent.run(question)