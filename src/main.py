"""
设备故障诊断 CLI

用法：
    cd "D:/software project/ai-diagnostic-agent"

    # Agent 模式（带工具调用，推荐）
    .venv/Scripts/python -m src.main

    # 普通对话模式（不带工具）
    .venv/Scripts/python -m src.main --chat

命令：
    /agent              - 切换到 Agent 模式
    /chat               - 切换到普通对话模式
    /switch claude|openai - 切换模型
    /clear              - 清空对话历史
    /quit               - 退出
"""
import sys
from src.llm.client import DiagnosticChat
from src.agent.diagnostic_agent import run_diagnosis
from langchain_core.messages import HumanMessage


def main():
    # 默认 Agent 模式，--chat 参数切换到普通对话模式
    mode = "chat" if "--chat" in sys.argv else "agent"
    provider = None

    # 解析 --provider 参数
    for i, arg in enumerate(sys.argv):
        if arg == "--provider" and i + 1 < len(sys.argv):
            provider = sys.argv[i + 1]

    print("=" * 60)
    print("🔧 SMYZE 饮吧设备 - 智能故障诊断助手")
    print("=" * 60)

    chat = None
    if mode == "chat":
        chat = DiagnosticChat(provider)
        print(f"模式: 普通对话 | 模型: {chat.provider_name}")
    else:
        print(f"模式: Agent (带工具调用)")

    print()
    print("命令: /agent  /chat  /switch claude|openai  /clear  /quit")
    print("-" * 60)

    while True:
        try:
            user_input = input("\n🧑 你: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if not user_input:
            continue

        # 命令处理
        if user_input.startswith("/"):
            cmd = user_input.lower().split()

            if cmd[0] == "/quit":
                print("再见！")
                break

            elif cmd[0] == "/agent":
                mode = "agent"
                print("✅ 已切换到 Agent 模式（带工具调用）")
                continue

            elif cmd[0] == "/chat":
                mode = "chat"
                if chat is None:
                    chat = DiagnosticChat(provider)
                print(f"✅ 已切换到普通对话模式 ({chat.provider_name})")
                continue

            elif cmd[0] == "/clear":
                if chat:
                    chat.clear_history()
                print("✅ 对话历史已清空")
                continue

            elif cmd[0] == "/switch" and len(cmd) > 1:
                provider = cmd[1]
                if chat:
                    try:
                        chat.switch_model(provider)
                    except Exception as e:
                        print(f"❌ 切换失败: {e}")
                        continue
                print(f"✅ 模型已切换到 {provider}")
                continue

            else:
                print("命令: /agent  /chat  /switch claude|openai  /clear  /quit")
                continue

        # 执行
        if mode == "agent":
            try:
                result = run_diagnosis(user_input, provider=provider, verbose=True)
                print(f"\n{'='*50}")
                print("📋 最终诊断结果:")
                print(f"{'='*50}")
                print(result)
            except Exception as e:
                print(f"\n❌ Agent 执行失败: {e}")
        else:
            # 普通对话模式
            print(f"\n🤖 [{chat.provider_name}]: ", end="", flush=True)
            try:
                for token in chat.stream_chat(user_input):
                    print(token, end="", flush=True)
                print()
            except Exception as e:
                print(f"\n❌ 调用失败: {e}")
                if chat.history and isinstance(chat.history[-1], HumanMessage):
                    chat.history.pop()


if __name__ == "__main__":
    main()
