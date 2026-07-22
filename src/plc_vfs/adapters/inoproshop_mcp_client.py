"""
InoProShop LIMIT MCP 的 stdio 客户端

通过 NDJSON（行分隔 JSON）与 Node.js bundle 通信，
复用 InoProShop_LIMIT_MCP 提供的工具能力。

不依赖 mcp SDK 的 ClientSession，避免 async/sync 混合问题。
"""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class InoProShopMCPError(RuntimeError):
    """MCP 调用返回错误"""
    pass


class InoProShopMCPClient:
    """
    最小 MCP stdio 客户端

    参数：
        command: 可执行文件，例如 "node"
        args: 传给可执行文件的参数列表，例如 ["bundle.min.js", "--codesys-path", ...]
        env: 可选环境变量字典
        timeout: 单次请求超时（秒）
    """

    def __init__(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout: float = 60.0,
    ):
        self.command = command
        self.args = args
        self.timeout = timeout

        self._proc = subprocess.Popen(
            [command, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            bufsize=0,
        )

        self._lock = threading.Lock()
        self._cond = threading.Condition()
        self._pending: Dict[int, Optional[Dict[str, Any]]] = {}
        self._next_id = 0
        self._closed = False

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

        self._stderr_reader = threading.Thread(target=self._read_stderr, daemon=True)
        self._stderr_reader.start()

        self._initialize()

    def _send(self, message: Dict[str, Any]) -> None:
        """发送一条 JSON-RPC 消息"""
        data = json.dumps(message, ensure_ascii=False) + "\n"
        try:
            self._proc.stdin.write(data.encode("utf-8"))
            self._proc.stdin.flush()
        except BrokenPipeError as e:
            raise InoProShopMCPError("InoProShop MCP 子进程已关闭") from e

    def _read_loop(self) -> None:
        """后台读取 stdout 的 JSON-RPC 响应/通知"""
        try:
            while True:
                raw = self._proc.stdout.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("收到非法 JSON: %s", line[:200])
                    continue
                self._handle_message(message)
        except Exception:
            logger.exception("MCP 读取循环异常")
        finally:
            with self._cond:
                self._closed = True
                self._cond.notify_all()

    def _read_stderr(self) -> None:
        """后台读取 stderr 并记录日志"""
        try:
            for raw in self._proc.stderr:
                line = raw.decode("utf-8", errors="replace").rstrip()
                if line:
                    logger.debug("[InoProShop MCP stderr] %s", line)
        except Exception:
            pass

    def _handle_message(self, message: Dict[str, Any]) -> None:
        """分发响应和通知"""
        msg_id = message.get("id")
        if msg_id is not None:
            with self._cond:
                self._pending[msg_id] = message
                self._cond.notify_all()
        else:
            method = message.get("method")
            logger.debug("收到通知: %s", method)

    def _request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """发送 JSON-RPC 请求并等待响应"""
        with self._lock:
            req_id = self._next_id
            self._next_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }

        with self._cond:
            self._pending[req_id] = None

        self._send(request)

        with self._cond:
            deadline = time.time() + self.timeout
            while (
                self._pending.get(req_id) is None
                and not self._closed
                and time.time() < deadline
            ):
                remaining = deadline - time.time()
                self._cond.wait(timeout=max(0.0, remaining))

            response = self._pending.pop(req_id, None)

        if response is None:
            raise TimeoutError(f"MCP 请求超时: {method}")

        if "error" in response:
            error = response["error"]
            raise InoProShopMCPError(
                f"MCP 错误 {error.get('code')}: {error.get('message')}"
            )

        return response.get("result")

    def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """发送 JSON-RPC 通知"""
        self._send({
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        })

    def _initialize(self) -> None:
        """完成 MCP initialize 握手"""
        result = self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "plc-mcp", "version": "0.1.0"},
            },
        )
        logger.debug("MCP initialize 结果: %s", result)
        self._send_notification("initialized", {})

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """
        调用一个 MCP Tool

        返回：
            如果 Tool 返回的是 JSON 文本，则自动反序列化为 Python 对象；
            否则返回原始字符串。
        """
        result = self._request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )

        # MCP Tool 返回的是 CallToolResult，内容在 content 列表里
        if isinstance(result, dict) and "content" in result:
            texts: List[str] = []
            for item in result["content"]:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(str(item.get("text", "")))
            text = "\n".join(texts)

            # 尝试解析为 JSON
            stripped = text.strip()
            if stripped and (stripped.startswith("{") or stripped.startswith("[")):
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    pass
            return stripped

        return result

    def close(self) -> None:
        """关闭子进程和读取线程"""
        self._closed = True
        try:
            self._proc.stdin.close()
        except Exception:
            pass

        try:
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except Exception:
            try:
                self._proc.kill()
                self._proc.wait(timeout=5)
            except Exception:
                pass

        self._reader.join(timeout=5)
        self._stderr_reader.join(timeout=5)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
