import sys
import os
from pathlib import Path

# প্রজেক্টের রুট পাথ এবং plan/Cnpi_RAG ডিরেক্টরিগুলো Python path-এ যুক্ত করা হচ্ছে
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir / "plan"))
sys.path.insert(0, str(current_dir / "Cnpi_RAG"))

from langchain_core.messages import HumanMessage, AIMessage

from Cnpi_RAG.graph import app
from plan.state import new_rag_state

def main():
    print("=" * 60)
    print("CNPI Hybrid RAG System - Local Testing Tool")
    print("=" * 60)
    print("গ্রাফ কম্পাইল করা হচ্ছে... (দয়া করে অপেক্ষা করুন)")
    
    try:
        compiled_graph = app.compile()
        print("✓ গ্রাফ সফলভাবে কম্পাইল হয়েছে!\n")
    except Exception as e:
        print(f"Error compiling graph: {e}")
        return

    # ★ Chat history — আগের কথোপকথন এখানে জমা হবে এবং প্রতিটা টার্নে
    #   AI-কে দেখানো হবে যাতে সে আগের মেসেজ মনে রাখতে পারে।
    chat_history: list = []

    while True:
        try:
            # ইউজারের কাছ থেকে ইনপুট নেওয়া
            user_question = input("\nআপনার প্রশ্ন লিখুন (বের হতে 'exit' লিখুন): ").strip()
            
            if user_question.lower() in ['exit', 'quit']:
                print("টেস্টিং শেষ করা হলো। ধন্যবাদ!")
                break
                
            if not user_question:
                continue

            print("\n🔍 উত্তর খোঁজা হচ্ছে...\n")
            
            # ★ স্টেট ইনিশিয়ালাইজেশন — আগের chat_history পাঠানো হচ্ছে
            initial_state = new_rag_state(
                user_input=user_question,
                messages=chat_history,
            )
            
            # গ্রাফ এক্সিকিউশন
            result_state = compiled_graph.invoke(initial_state)
            
            # আউটপুট প্রিন্ট করা
            print("=" * 60)
            print("🤖 বটের উত্তর:")
            final_ans = result_state.get("final_answer", "")
            
            # If top-level final_answer is empty, try to get it from the nested state
            decided_path = result_state.get("decided_path")
            if not final_ans and decided_path:
                path_state = result_state.get(decided_path, {})
                final_ans = path_state.get("final_answer", "")
                
            if final_ans:
                print(final_ans)
            else:
                print("(কোনো উত্তর জেনারেট হয়নি)")
            print("-" * 60)
            
            # ★ Chat history আপডেট — এই টার্নের মানুষ ও AI মেসেজ যোগ করা
            chat_history = result_state.get("messages", [])
            # যদি কোনো কারণে messages স্টেটে না থাকে, তবে নিজে যোগ করি
            if not chat_history:
                chat_history.append(HumanMessage(content=user_question))
                chat_history.append(AIMessage(content=final_ans or "(কোনো উত্তর নেই)"))
            
            # ডিবাগ বা স্টেট ইনফরমেশন (Testing এর জন্য)
            print("🛠️ ডিবাগ ইনফো:")
            print(f"  - Rewritten Query: {result_state.get('rewritten_query')}")
            print(f"  - Normalized Qry : {result_state.get('normalized_query')}")
            print(f"  - Answer Status  : {result_state.get('answer_status')}")
            print(f"  - Decided Path   : {result_state.get('decided_path')}")
            print(f"  - Chat History   : {len(chat_history)} messages")
            
            # যদি হাইব্রিড পাথ ব্যবহার হয়ে থাকে, তবে তার ভেতরের অবস্থা
            if result_state.get('decided_path') == 'hybrid':
                hybrid_data = result_state.get('hybrid', {})
                print(f"  - Hybrid Depth     : {hybrid_data.get('depth')}")
                print(f"  - Sub-Queries Gen  : {hybrid_data.get('total_sub_q')}")
                print(f"  - Sub-Queries Ans  : {hybrid_data.get('sub_ans_count')}")
                print(f"  - Sub-Query List   : {hybrid_data.get('sub_query_list')}")
            print("=" * 60)

        except KeyboardInterrupt:
            print("\nটেস্টিং বন্ধ করা হলো।")
            break
        except Exception as e:
            print(f"\n❌ এরর হয়েছে: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
