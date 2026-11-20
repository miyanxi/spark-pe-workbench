"""DeepSeek 官方 API 客户端。"""

import os
import sys
from typing import Any, Dict, List, Optional

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import API_ENDPOINT, API_KEY, API_TIMEOUT, TEXT_MODEL


class DeepSeekAPIError(RuntimeError):
    """可安全展示给上层的 DeepSeek 调用错误。"""


class DeepSeekClient:
    """调用 DeepSeek 官方 OpenAI 兼容 Chat Completions 接口。"""

    def __init__(self) -> None:
        self.api_key = API_KEY
        self.endpoint = API_ENDPOINT.rstrip("/")
        self.timeout = API_TIMEOUT
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """生成文本；失败时抛出不包含 API 密钥的错误。"""
        if not self.api_key:
            raise DeepSeekAPIError("AI 生成功能尚未配置 API Key。演示数据和图表可正常使用；如需生成内容，请配置自己的密钥后重启服务。")
        payload: Dict[str, Any] = {
            "model": model or TEXT_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": False,
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            response = requests.post(
                f"{self.endpoint}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise DeepSeekAPIError("DeepSeek 响应超时，请检查网络后重试") from exc
        except requests.RequestException as exc:
            raise DeepSeekAPIError("无法连接 DeepSeek，请检查网络连接") from exc

        if not response.ok:
            detail = ""
            try:
                error_data = response.json().get("error", {})
                detail = error_data.get("message", "")
            except (ValueError, AttributeError):
                pass
            if response.status_code in (401, 403):
                raise DeepSeekAPIError("DeepSeek API 密钥无效或没有访问权限")
            if response.status_code == 429:
                raise DeepSeekAPIError("DeepSeek 请求过于频繁或账户余额不足，请稍后重试")
            suffix = f"：{detail}" if detail else ""
            raise DeepSeekAPIError(f"DeepSeek 调用失败（HTTP {response.status_code}）{suffix}")

        try:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise DeepSeekAPIError("DeepSeek 返回了无法识别的数据格式") from exc

        if not isinstance(content, str) or not content.strip():
            raise DeepSeekAPIError("DeepSeek 未返回有效内容")
        return content.strip()


deepseek_client = DeepSeekClient()
