import os
import requests
from typing import List, Dict

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="C:/Users/Lenovo/Desktop/py/5.25/.env")
except ImportError:
    pass

class HelloAgentsLLM:
    """
    为本书 "Hello Agents" 定制的LLM客户端。
    调用 MiniMax M2.7（Anthropic 兼容格式）。
    """
    def __init__(self, model: str = None, apiKey: str = None, baseUrl: str = None, timeout: int = None):
        """
        初始化客户端。优先使用传入参数，如果未提供，则从环境变量加载。
        """
        self.model = model or os.getenv("LLM_MODEL_ID")
        self.apiKey = apiKey or os.getenv("LLM_API_KEY")
        self.baseUrl = baseUrl or os.getenv("LLM_BASE_URL") or "https://api.minimaxi.com/anthropic"
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))

        if not all([self.model, self.apiKey]):
            raise ValueError("模型ID和API密钥必须被提供或在.env文件中定义。")

    def think(self, messages: List[Dict[str, str]], temperature: float = 0, max_tokens: int = 2048) -> str:
        """
        调用大语言模型进行思考，并返回其响应。
        """
        print(f"正在调用 {self.model} 模型...")
        try:
            # 转换消息格式（OpenAI -> Anthropic）
            anthropic_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    anthropic_messages.append({"role": "user", "content": f"[System] {msg['content']}"})
                else:
                    anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

            response = requests.post(
                f"{self.baseUrl}/v1/messages",
                headers={
                    "X-Api-Key": self.apiKey,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": anthropic_messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True
                },
                timeout=self.timeout,
                stream=True
            )

            print(f"大语言模型响应成功:")
            collected_content = []
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        import json
                        try:
                            chunk = json.loads(data)
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text", "")
                                    print(text, end="", flush=True)
                                    collected_content.append(text)
                        except:
                            pass
            print()
            return "".join(collected_content)

        except Exception as e:
            print(f"调用LLM API时发生错误: {e}")
            return None