"""
flows.py + loader.py 自检脚本

怎么跑：
    cd D:\\QWER\\Projects\\ecommerce-customer-service\\customer-service-backend
    uv run python check_flows.py

它干啥：
    用你自己写的 FlowLoader，把两份真实 yml 读成 FlowsList，
    再检查 Flow / FlowsList 上的查询方法是不是真的能用。

（之前这里有个"简易版 loader"垫着，现在你的 loader.py 写好了，
  已经把它删掉，直接用你的正式版。）
"""

from pathlib import Path

from construction_service.task.flow.loader import FlowLoader

YML_FILES = ["user_flows.yml", "system_flows.yml"]


def main():
    # ① 准备真实输入（两份 yml 的路径）
    paths = [Path("flow_config") / fname for fname in YML_FILES]

    # ② 调用你的代码：读文件 -> 总表
    flows_list = FlowLoader().load_many_yaml(paths)

    print(f"总表：{len(flows_list.flows)} 条流程，{len(flows_list.slots)} 个全局槽位")
    print(f"全局槽位：{list(flows_list.slots.keys())}")
    print()
    for f in flows_list.flows:
        print(f"  {f.flow_id:32s} {len(f.steps)}步  槽位={list(f.slots.keys())}")
    print()

    # ③ 断言
    assert len(flows_list.flows) == 12, "应该读到 12 条流程"
    assert len(flows_list.slots) == 8, "应该有 8 个全局槽位"

    # 按 id 找流程
    flow = flows_list.get_flow_by_id("refund_request")
    assert flow is not None, "应该能找到退款流程"
    assert flow.flow_name == "退款申请"
    assert list(flow.slots.keys()) == ["order_number", "refund_reason"], "退款流程应该只带这 2 个槽位"
    print(f"找 refund_request -> {flow.flow_name}，{len(flow.steps)} 步，槽位={list(flow.slots.keys())}")

    # 找入口步骤
    start = flow.get_start_step()
    assert start is not None and start.id == "start", "应该能找到入口步骤"
    print(f"入口步骤 -> {type(start).__name__} id={start.id}")

    # 按 id 找步骤
    step = flow.get_step_by_id("ask_refund_reason")
    assert step is not None and step.slot_name == "refund_reason"
    print(f"找 ask_refund_reason -> {type(step).__name__} 收集槽位={step.slot_name}")

    # 找不到时应该返回 None
    assert flows_list.get_flow_by_id("not_exist") is None
    assert flow.get_step_by_id("not_exist") is None
    print("找不存在的流程/步骤 -> 都返回 None")

    print("\n全部断言通过 ✅")


if __name__ == "__main__":
    main()
