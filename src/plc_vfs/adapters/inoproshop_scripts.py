"""
InoProShop / CODESYS IronPython 脚本模板库

所有脚本均兼容 CODESYS SP11 内置的 IronPython 2.7，
通过 InoProShop.exe --runscript=<script.py> 执行。

脚本规范：
- 使用 rlog() 输出到结果文件（由 ScriptRunner 注入前缀）
- 成功时打印 SCRIPT_SUCCESS: <msg>
- 失败时打印 SCRIPT_ERROR: <msg> 并 sys.exit(1)
"""

from __future__ import annotations

import json
import textwrap
from typing import Optional


# ---------------------------------------------------------------------------
# 通用辅助函数（会被注入到每个脚本顶部）
# ---------------------------------------------------------------------------

COMMON_HELPERS = textwrap.dedent(
    r'''
    def _find_object_by_path(root, path_parts, expected_type=None):
        """按路径列表在项目树中查找对象。"""
        target = root
        for part in path_parts:
            if target is None:
                return None
            found = None
            children = getattr(target, "children", None) or []
            for child in children:
                if getattr(child, "name", None) == part:
                    found = child
                    break
            if found is None:
                return None
            target = found
        return target

    def _find_child_by_name(parent, name):
        if parent is None:
            return None
        children = getattr(parent, "children", None) or []
        for child in children:
            if getattr(child, "name", None) == name:
                return child
        return None
    '''
).strip()


# ---------------------------------------------------------------------------
# 脚本构建函数
# ---------------------------------------------------------------------------

def _script_body(core_code: str) -> str:
    """把核心代码包上 helpers + try/except 外壳，并保证缩进正确。"""
    indented_core = textwrap.indent(core_code.strip(), "    ")
    return (
        COMMON_HELPERS
        + "\n\n"
        + "try:\n"
        + indented_core
        + "\nexcept Exception as e:\n"
        + "    rlog(\"SCRIPT_ERROR: \" + str(e))\n"
        + "    rlog(traceback.format_exc())\n"
        + "    sys.exit(1)\n"
    )


def build_open_project(project_path: str) -> str:
    """打开已有 .project 工程文件。"""
    core = textwrap.dedent(
        f'''
        projects = scriptengine.projects
        primary = projects.primary
        if primary is not None and primary.path == r"{project_path}":
            rlog("Project already open: " + primary.path)
        else:
            primary = projects.open(r"{project_path}")
            rlog("Opened project: " + primary.path)
        rlog("SCRIPT_SUCCESS: open_project")
        sys.exit(0)
        '''
    ).strip()
    return _script_body(core)


def build_create_project(project_path: str, template_path: str) -> str:
    """从模板工程文件复制创建新项目。"""
    core = textwrap.dedent(
        f'''
        import shutil

        target_dir = os.path.dirname(r"{project_path}")
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        if os.path.exists(r"{project_path}"):
            rlog("SCRIPT_ERROR: target project already exists")
            sys.exit(1)
        shutil.copy(r"{template_path}", r"{project_path}")
        rlog("Created project from template: " + r"{template_path}")
        projects = scriptengine.projects
        proj = projects.open(r"{project_path}")
        rlog("Opened newly created project: " + proj.path)
        rlog("SCRIPT_SUCCESS: create_project")
        sys.exit(0)
        '''
    ).strip()
    return _script_body(core)


def build_get_project_structure() -> str:
    """获取项目对象树（递归），输出 JSON。"""
    core = textwrap.dedent(
        r'''
        def _node_to_dict(node):
            result = {}
            name = getattr(node, "name", None)
            if name is not None:
                result["name"] = str(name)
            node_type = getattr(node, "type", None)
            if node_type is not None:
                result["type"] = str(node_type)
            children = getattr(node, "children", None)
            if children:
                result["children"] = [_node_to_dict(c) for c in children]
            return result

        projects = scriptengine.projects
        primary = projects.primary
        if primary is None:
            rlog("SCRIPT_ERROR: no primary project")
            sys.exit(1)
        tree = _node_to_dict(primary)
        rlog(json.dumps(tree, ensure_ascii=False))
        rlog("SCRIPT_SUCCESS: get_project_structure")
        sys.exit(0)
        '''
    ).strip()
    return _script_body(core)


def build_get_pou_code(pou_path: str) -> str:
    """读取指定 POU 的 declaration 和 implementation。"""
    core = textwrap.dedent(
        f'''
        projects = scriptengine.projects
        primary = projects.primary
        if primary is None:
            rlog("SCRIPT_ERROR: no primary project")
            sys.exit(1)

        target = _find_object_by_path(primary, ["{pou_path}"])
        if target is None:
            # 兼容某些版本把 POU 放在 Application 下
            target = _find_object_by_path(primary, ["Application", "{pou_path}"])
        if target is None:
            rlog("SCRIPT_ERROR: POU not found: {pou_path}")
            sys.exit(1)

        text = getattr(target, "text", None)
        if text is None:
            rlog("SCRIPT_ERROR: POU has no text attribute")
            sys.exit(1)

        full_code = str(text)
        # CODESYS 通常把声明和实现放在同一个文本里。
        # 这里先整体返回，由调用方按 END_VAR 拆分。
        result = {{"declaration": "", "implementation": full_code}}
        rlog(json.dumps(result, ensure_ascii=False))
        rlog("SCRIPT_SUCCESS: get_pou_code")
        sys.exit(0)
        '''
    ).strip()
    return _script_body(core)


def build_create_pou(name: str, pou_type: str) -> str:
    """在 Application 下创建 POU。"""
    core = textwrap.dedent(
        f'''
        projects = scriptengine.projects
        primary = projects.primary
        if primary is None:
            rlog("SCRIPT_ERROR: no primary project")
            sys.exit(1)

        app = _find_object_by_path(primary, ["Application"])
        if app is None:
            app = primary

        existing = _find_child_by_name(app, "{name}")
        if existing is not None:
            rlog("SCRIPT_ERROR: POU already exists: {name}")
            sys.exit(1)

        new_pou = app.create_child("{pou_type}", "{name}")
        rlog("Created POU: {name} ({pou_type})")
        rlog("SCRIPT_SUCCESS: create_pou")
        sys.exit(0)
        '''
    ).strip()
    return _script_body(core)


def build_set_pou_code(pou_path: str, declaration: str, implementation: str) -> str:
    """写入 POU 源码。"""
    # 用 repr() 把多行字符串变成合法的单行 Python 字面量，避免缩进破坏三引号字符串
    decl_literal = repr(declaration)
    impl_literal = repr(implementation)

    core = textwrap.dedent(
        f'''
        projects = scriptengine.projects
        primary = projects.primary
        if primary is None:
            rlog("SCRIPT_ERROR: no primary project")
            sys.exit(1)

        target = _find_object_by_path(primary, ["{pou_path}"])
        if target is None:
            target = _find_object_by_path(primary, ["Application", "{pou_path}"])
        if target is None:
            rlog("SCRIPT_ERROR: POU not found: {pou_path}")
            sys.exit(1)

        decl = {decl_literal}
        impl = {impl_literal}
        full_code = decl + "\\n\\n" + impl if decl else impl
        target.text = full_code
        rlog("Set POU code: {pou_path}")
        rlog("SCRIPT_SUCCESS: set_pou_code")
        sys.exit(0)
        '''
    ).strip()
    return _script_body(core)


def build_save_project() -> str:
    """保存当前项目。"""
    core = textwrap.dedent(
        r'''
        projects = scriptengine.projects
        primary = projects.primary
        if primary is None:
            rlog("SCRIPT_ERROR: no primary project")
            sys.exit(1)
        primary.save()
        rlog("Project saved")
        rlog("SCRIPT_SUCCESS: save_project")
        sys.exit(0)
        '''
    ).strip()
    return _script_body(core)


def build_compile_project() -> str:
    """编译主应用并返回错误/警告统计。"""
    core = textwrap.dedent(
        r'''
        projects = scriptengine.projects
        primary = projects.primary
        if primary is None:
            rlog("SCRIPT_ERROR: no primary project")
            sys.exit(1)

        app = _find_object_by_path(primary, ["Application"])
        if app is None:
            app = primary

        result = app.compile()
        state = str(getattr(result, "state", "Unknown"))
        errors = getattr(result, "error_count", 0) or 0
        warnings = getattr(result, "warning_count", 0) or 0
        messages = getattr(result, "messages", None) or []
        msg_texts = [str(m) for m in messages]

        output = {
            "success": state.lower() in ("success", "succeeded"),
            "state": state,
            "errors": errors,
            "warnings": warnings,
            "messages": msg_texts,
        }
        rlog(json.dumps(output, ensure_ascii=False))
        rlog("SCRIPT_SUCCESS: compile_project")
        sys.exit(0)
        '''
    ).strip()
    return _script_body(core)


def build_probe_api(mode: str, target_path: Optional[str] = None, custom_code: Optional[str] = None) -> str:
    """探查 SP11 IronPython API（调试用）。"""
    target = target_path or ""
    code_literal = repr(custom_code or "")
    core = textwrap.dedent(
        f'''
        projects = scriptengine.projects
        primary = projects.primary
        target = primary
        path_parts = [p for p in r"{target}".split("/") if p]
        if path_parts:
            found = _find_object_by_path(primary, path_parts)
            if found is not None:
                target = found

        mode = "{mode}"
        if mode == "dir":
            rlog("dir(target): " + str(dir(target)))
        elif mode == "children":
            children = getattr(target, "children", None)
            if children:
                for i, c in enumerate(children):
                    rlog("child %d: %s" % (i, getattr(c, "name", "?")))
            else:
                rlog("no children")
        elif mode == "custom":
            probe_obj = target
            exec({code_literal})
        else:
            rlog("unknown mode: " + mode)

        rlog("SCRIPT_SUCCESS: probe_api")
        sys.exit(0)
        '''
    ).strip()
    return _script_body(core)
