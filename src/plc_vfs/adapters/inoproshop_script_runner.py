"""
InoProShop / CODESYS IronPython 脚本执行器

负责把 IronPython 脚本写入临时文件，并启动 InoProShop.exe
通过 --runscript 参数执行，最后读取结果文件中的输出。

设计目标：
- 生成 .py 脚本 -> spawn CODESYS -> 解析 SCRIPT_SUCCESS/SCRIPT_ERROR
- 不依赖外部 Node.js bundle，纯 Python 实现
- 与 TIA Portal 适配器一样，直接通过 IDE 自动化接口操作项目
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class InoProShopScriptError(RuntimeError):
    """脚本执行返回错误。"""
    pass


class InoProShopScriptRunner:
    """
    InoProShop IronPython 脚本运行器

    参数：
        codesys_path: InoProShop.exe / CODESYS.exe 完整路径
        profile: CODESYS profile 名称，例如 "InoProShop(V1.9.0.1)"
        workspace: 工程目录，用于相对路径解析
        timeout: 单次脚本执行超时（秒）
        keep_last_script: 是否在 %TEMP%/codesys_last_script.py 保留最后一次脚本
    """

    SUCCESS_MARKER = "SCRIPT_SUCCESS"
    ERROR_MARKER = "SCRIPT_ERROR"

    def __init__(
        self,
        codesys_path: str,
        profile: str,
        workspace: Optional[str] = None,
        timeout: float = 300.0,
        keep_last_script: bool = True,
    ):
        self.codesys_path = os.path.abspath(codesys_path)
        self.profile = profile
        self.workspace = os.path.abspath(workspace or os.path.dirname(self.codesys_path))
        self.timeout = timeout
        self.keep_last_script = keep_last_script

        if not os.path.exists(self.codesys_path):
            raise FileNotFoundError(f"CODESYS 可执行文件不存在: {self.codesys_path}")

    # -----------------------------------------------------------------------
    # 公开 API
    # -----------------------------------------------------------------------

    def run(self, script_body: str) -> Dict[str, Any]:
        """
        执行一段 IronPython 脚本并返回结果。

        返回：
            {"success": bool, "output": str}
        """
        script_file, result_file = self._prepare_files(script_body)
        try:
            return self._spawn_and_wait(script_file, result_file)
        finally:
            self._cleanup(script_file, result_file)

    def run_script(self, name: str, script_body: str) -> Dict[str, Any]:
        """带日志包装的 run()。"""
        logger.info("InoProShop script: %s", name)
        return self.run(script_body)

    # -----------------------------------------------------------------------
    # 内部实现
    # -----------------------------------------------------------------------

    def _prepare_files(self, script_body: str) -> tuple[str, str]:
        """生成临时脚本文件和结果文件。"""
        uid = f"{int(time.time() * 1000)}_{os.getpid()}_{threading.current_thread().ident}"
        tmp_dir = tempfile.gettempdir()
        script_file = os.path.join(tmp_dir, f"codesys_script_{uid}.py")
        result_file = os.path.join(tmp_dir, f"codesys_result_{uid}.txt")

        full_script = self._build_full_script(result_file, script_body)

        with open(script_file, "w", encoding="utf-8") as f:
            f.write(full_script)

        logger.debug("Script written to %s", script_file)
        return script_file, result_file

    def _build_full_script(self, result_file: str, script_body: str) -> str:
        """
        给业务脚本加上标准前缀：
        - 导入 sys/os/traceback/scriptengine
        - 设置 prompt_handling 自动处理弹窗
        - 定义 rlog() 把输出写入结果文件
        """
        # 把业务脚本里的 print("SCRIPT_SUCCESS...") 等转成 rlog，
        # 这样即使脚本作者混用 print 也能正确落盘。
        transformed = self._transform_prints(script_body)

        prefix = f'''# -*- coding: utf-8 -*-
import sys as _sys, os as _os, traceback as _tb
import scriptengine as _se_hdr
scriptengine = _se_hdr

# SP11: auto-dismiss all dialogs during scripted operations
try:
    _se_hdr.system.prompt_handling = _se_hdr.PromptHandling.ProcessScriptPrompts
except Exception:
    pass

_RESULT_FILE = r"{result_file}"

def rlog(s):
    try:
        with open(_RESULT_FILE, "ab") as _f:
            _f.write((str(s) + "\\n").encode("utf-8"))
    except Exception:
        pass

'''
        return prefix + transformed

    def _transform_prints(self, script_body: str) -> str:
        """把 print(...) 统一替换成 rlog(...)，避免输出丢失。"""
        # 仅替换顶层的 print( 调用； IronPython 2.7 没有 f-string，
        # 这里用简单字符串替换即可。
        transformed = script_body.replace("\r\n", "\n")
        # 保留字符串内的 print 不被替换是困难的，实际业务脚本中
        # print 只出现在 rlog/SCRIPT 标记处，所以直接替换即可。
        transformed = transformed.replace("print(", "rlog(")
        return transformed

    def _spawn_and_wait(self, script_file: str, result_file: str) -> Dict[str, Any]:
        """启动 CODESYS 进程并等待脚本执行结果。"""
        args = [
            f"--profile={self.profile}",
            f"--runscript={script_file}",
        ]

        env = os.environ.copy()
        codesys_dir = os.path.dirname(self.codesys_path)
        env["PATH"] = f"{codesys_dir};{env.get('PATH', '')}"

        logger.info("Spawning %s %s", self.codesys_path, " ".join(args))

        proc = subprocess.Popen(
            [self.codesys_path, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.workspace,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        finished = threading.Event()
        result: Dict[str, Any] = {"success": False, "output": ""}

        def read_stream(stream, collector):
            try:
                for line in iter(stream.readline, b""):
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").rstrip()
                    collector.append(text)
                    logger.debug("[codesys] %s", text)
            except Exception:
                pass

        stdout_thread = threading.Thread(target=read_stream, args=(proc.stdout, stdout_lines), daemon=True)
        stderr_thread = threading.Thread(target=read_stream, args=(proc.stderr, stderr_lines), daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        def poll_result_file():
            """轮询结果文件，出现成功/失败标记时返回。"""
            try:
                if not os.path.exists(result_file):
                    return None
                with open(result_file, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if self.SUCCESS_MARKER in content or self.ERROR_MARKER in content:
                    return content
            except Exception:
                pass
            return None

        def finalize(success: bool, output: str):
            if not finished.is_set():
                result["success"] = success
                result["output"] = output
                finished.set()
                try:
                    proc.kill()
                except Exception:
                    pass

        # 主等待循环
        start_time = time.time()
        poll_interval = 2.0
        last_poll = 0.0

        while not finished.is_set():
            now = time.time()
            if now - start_time > self.timeout:
                output = self._read_file(result_file) + "\n" + "\n".join(stderr_lines)
                finalize(False, f"SCRIPT_ERROR: Timeout after {self.timeout}s\n{output}")
                break

            if now - last_poll >= poll_interval:
                content = poll_result_file()
                if content is not None:
                    success = self.SUCCESS_MARKER in content
                    finalize(success, content)
                    break
                last_poll = now

            # 检查进程是否已退出
            ret = proc.poll()
            if ret is not None:
                # 进程结束后再读一次结果文件
                time.sleep(0.5)
                content = self._read_file(result_file)
                combined = content + "\n" + "\n".join(stderr_lines)
                if self.SUCCESS_MARKER in combined:
                    finalize(True, content)
                elif self.ERROR_MARKER in combined:
                    finalize(False, content)
                else:
                    finalize(False, f"SCRIPT_ERROR: Process exited {ret}\n{combined}")
                break

            time.sleep(0.2)

        stdout_thread.join(timeout=2)
        stderr_thread.join(timeout=2)
        proc.wait(timeout=5)

        if not result["success"] and not result["output"].strip():
            result["output"] = "SCRIPT_ERROR: No output captured"

        return result

    def _read_file(self, path: str) -> str:
        """安全读取文件内容。"""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return ""

    def _cleanup(self, script_file: str, result_file: str) -> None:
        """清理临时文件，可选保留最后一份脚本用于调试。"""
        if self.keep_last_script:
            try:
                last = os.path.join(tempfile.gettempdir(), "codesys_last_script.py")
                shutil.copy2(script_file, last)
            except Exception:
                pass

        for path in (script_file, result_file):
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.warning("Failed to remove temp file %s: %s", path, e)

    # -----------------------------------------------------------------------
    # 便捷方法：直接映射到 PLCAdapter 需要的能力
    # -----------------------------------------------------------------------

    def open_project(self, project_path: str) -> Dict[str, Any]:
        from . import inoproshop_scripts as scripts

        return self.run_script("open_project", scripts.build_open_project(project_path))

    def create_project(self, project_path: str, template_path: str) -> Dict[str, Any]:
        from . import inoproshop_scripts as scripts

        return self.run_script(
            "create_project", scripts.build_create_project(project_path, template_path)
        )

    def get_project_structure(self) -> Dict[str, Any]:
        from . import inoproshop_scripts as scripts

        return self.run_script("get_project_structure", scripts.build_get_project_structure())

    def get_pou_code(self, pou_path: str) -> Dict[str, Any]:
        from . import inoproshop_scripts as scripts

        return self.run_script("get_pou_code", scripts.build_get_pou_code(pou_path))

    def create_pou(self, name: str, pou_type: str) -> Dict[str, Any]:
        from . import inoproshop_scripts as scripts

        return self.run_script("create_pou", scripts.build_create_pou(name, pou_type))

    def set_pou_code(self, pou_path: str, declaration: str, implementation: str) -> Dict[str, Any]:
        from . import inoproshop_scripts as scripts

        return self.run_script(
            "set_pou_code",
            scripts.build_set_pou_code(pou_path, declaration, implementation),
        )

    def save_project(self) -> Dict[str, Any]:
        from . import inoproshop_scripts as scripts

        return self.run_script("save_project", scripts.build_save_project())

    def compile_project(self) -> Dict[str, Any]:
        from . import inoproshop_scripts as scripts

        return self.run_script("compile_project", scripts.build_compile_project())

    def probe_api(
        self,
        mode: str,
        target_path: Optional[str] = None,
        custom_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        from . import inoproshop_scripts as scripts

        return self.run_script(
            "probe_api",
            scripts.build_probe_api(mode, target_path, custom_code),
        )
