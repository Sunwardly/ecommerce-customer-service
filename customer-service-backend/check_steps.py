"""
steps.py 自检脚本（端到端测试）

怎么跑：
    cd D:\\QWER\\Projects\\ecommerce-customer-service\\customer-service-backend
    uv run python check_steps.py

它干什么：
    拿真实的 flow_config/*.yml 文件，喂给你写的 steps.py，
    看它能不能把 yml 里的文本，正确解析成一个个 FlowStep 对象。

为什么叫"端到端"(end-to-end)：
    输入用的是"最真实的文件"，不是自己编的假数据；
    中间不跳过任何一步，从头走到尾，看最后结果对不对。
"""

import yaml
from pathlib import Path

from construction_service.task.flow.steps import (
    FlowStep, StartFlowStep, EndFlowStep, ActionFlowStep, CollectFlowStep,
)
from construction_service.task.flow.links import FlowStepConditionLink, FlowStepFallbackLink

# 要检查的 yml 文件（相对路径，所以必须在项目根目录下运行）
YML_FILES = ["user_flows.yml", "system_flows.yml"]


def short(link):
    """把一条边显示成短名字，比如 Static->ask_order_number"""
    name = type(link).__name__.replace("FlowStep", "").replace("Link", "")
    return f"{name}->{link.target}"


def show(step):
    """打印一个步骤的关键信息（便于肉眼检查）"""
    extra = ""
    if isinstance(step, CollectFlowStep):
        extra = f"  slot={step.slot_name}"
    elif isinstance(step, ActionFlowStep):
        extra = f"  action={step.action}  args={step.args!r}"
    print(f"    {type(step).__name__:16s} {step.id:22s} {[short(l) for l in step.next]}{extra}")


def run_through_real_files():
    """第一段：把真实 yml 全部解析一遍，打印出来看"""
    total = 0
    for fname in YML_FILES:
        # 第 1 步：读文件 → yml 文本
        text = (Path("flow_config") / fname).read_text(encoding="utf-8")
        # 第 2 步：yml 文本 → Python 字典（这一步是 yaml 库的活）
        data = yaml.safe_load(text)
        flows = data["flows"]

        print(f"########## {fname}（{len(flows)} 个流程）##########")
        for flow_id, flow_body in flows.items():
            print(f"--- {flow_id} ---")
            for step_data in flow_body["steps"]:
                # 第 3 步：字典 → FlowStep 对象（这一步是"你的代码"）
                step = FlowStep.from_dict(step_data)
                show(step)
                total += 1
        print()
    print(f"合计解析 {total} 个步骤\n")


def run_assertions():
    """第二段：断言。把"我觉得对"变成"机器帮我确认"。"""
    # 1. start 步骤 → StartFlowStep，静态边指向正确
    s = FlowStep.from_dict({"id": "start", "type": "start", "next": "ask"})
    assert isinstance(s, StartFlowStep), "start 步骤应该解析成 StartFlowStep"
    assert s.next[0].target == "ask", "静态边应该指向 ask"

    # 2. 条件边：一个 if + 一个 else，应该解析出 2 条边
    s = FlowStep.from_dict({"id": "start", "type": "start",
                            "next": [{"if": "a", "then": "b"}, {"else": "c"}]})
    assert len(s.next) == 2, "应该有两条边"
    assert isinstance(s.next[0], FlowStepConditionLink), "第一条应该是条件边"
    assert isinstance(s.next[1], FlowStepFallbackLink), "第二条应该是兜底边"

    # 3. 空 next（end 步骤）不能报错
    s = FlowStep.from_dict({"id": "end", "type": "end", "next": []})
    assert s.next == [], "空 next 应该解析成空列表"

    # 4. collect 步骤：槽位名和问用户的话
    s = FlowStep.from_dict({"id": "ask", "type": "collect", "next": "x",
                            "slot_name": "order_number",
                            "response": {"text": "请告诉我你的订单号。"}})
    assert isinstance(s, CollectFlowStep)
    assert s.slot_name == "order_number"
    assert s.response.text == "请告诉我你的订单号。"
    assert s.validate is None, "yml 里没写 validate 时，应该是 None"

    # 5. action 步骤没写 args 时，应该是空字典 {}
    s = FlowStep.from_dict({"id": "do", "type": "action",
                            "action": "action_lookup_order_status", "next": "x"})
    assert isinstance(s, ActionFlowStep)
    assert s.args is None, "没写 args 应保持现有契约的 None"

    print("全部断言通过 ✅")


if __name__ == "__main__":
    run_through_real_files()
    run_assertions()
