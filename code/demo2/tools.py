"""
工具集模块
定义所有可用的工具及其执行逻辑
"""

import datetime
from typing import Callable, Dict


class Tool:
    """工具基类"""

    def __init__(self, name: str, description: str, func: Callable):
        self.name = name
        self.description = description
        self.func = func

    def run(self, *args, **kwargs) -> str:
        """执行工具函数"""
        try:
            return self.func(*args, **kwargs)
        except Exception as e:
            return f"[{self.name}] 执行错误: {e}"


def calculator_func(expression: str) -> str:
    """计算器工具函数"""
    try:
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {e}"


def get_time_func() -> str:
    """获取当前时间工具函数"""
    now = datetime.datetime.now()
    return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"


def string_length_func(text: str) -> str:
    """字符串长度工具函数"""
    return f"字符串长度: {len(text)}"


# 注册所有工具
TOOLS: Dict[str, Tool] = {
    "calculator": Tool(
        name="计算器",
        description="计算数学表达式,如: 123+456",
        func=calculator_func
    ),
    "get_time": Tool(
        name="时间查询",
        description="获取当前时间",
        func=get_time_func
    ),
    "string_length": Tool(
        name="字符串长度",
        description="计算字符串的长度",
        func=string_length_func
    )
}


def get_tools_description() -> str:
    """获取所有工具的描述信息"""
    descriptions = []
    for tool_id, tool in TOOLS.items():
        descriptions.append(f"- {tool_id}: {tool.description}")
    return "\n".join(descriptions)
