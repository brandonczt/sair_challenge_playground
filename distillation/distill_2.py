import os
import re
from openai import OpenAI

# --- 配置区 ---
client = OpenAI(
    api_key="", 
    base_url="https://api.linkapi.ai/v1"
)

# 第一阶段生成的文件名
# STAGE1_FILES = ["analysis_TP.txt", "analysis_TN.txt", "analysis_FP.txt", "analysis_TP_1.txt", "analysis_TN_1.txt", "analysis_FP_1.txt", "analysis_FN.txt"]
STAGE1_FILES = ["analysis_FN.txt"]
# 每多少个 Batch 报告合并成一个局部汇总？建议 5-10 个
SUMMARIZE_CHUNK_SIZE = 7
TARGET_MODEL = "[次]gemini-3.1-pro-preview"

# --- 提示词：2.1 类别内批次归纳 ---
CONSOLIDATION_PROMPT_TEMPLATE = """
**Background:** We are participating in the "Equational Theories" mathematics challenge. The task involves proving or disproving whether `equation1` implies `equation2` within a specific equational theory. We are synthesizing multiple batch analysis reports from the Equational Theory competition.
Task: Universal Pattern Extraction (Category: {BUCKET_NAME})

Objective: 
Below are several individual batch reports. Synthesize them into a single, high-density Category Master Report. 

Instructions:
1. Identify Redundancies: Group recurring strategies or errors into "Core Pillars."
2. Filter Noise: Remove specific problem IDs or one-off errors. Keep only universal logical patterns.
3. Rank by Impact: Identify the top 3-5 high-frequency patterns that are most critical.
4. Extract Actionable Logic: Convert observations into specific derivation rules or refutation triggers.


Format: Use a highly structured list:
Key Logical Patterns (Successful strategies): (For TP/FN)
Critical Failure Points (Specific pitfalls/hallucinations to avoid): (For FP/FN)
Refutation Heuristics (When to stop proving and start disproving): (For TN)

Constraint: Keep the final summary concise.
"""

def parse_blocks(file_path):
    """解析第一阶段文件，提取出每一个 Batch 的内容"""
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 使用正则表达式分割 Batch 块
    blocks = re.split(r"--- Batch \d+ Analysis ---", content)
    # 过滤掉空块
    return [b.strip() for b in blocks if len(b.strip()) > 50]

def summarize_blocks(bucket_name, blocks):
    """将多个块合并并调用 LLM 进行归纳"""
    combined_text = "\n\n=== NEXT BATCH REPORT ===\n\n".join(blocks)
    
    prompt = CONSOLIDATION_PROMPT_TEMPLATE.format(BUCKET_NAME=bucket_name)
    user_content = f"{prompt}\n\nReports to Synthesize:\n{combined_text}"
    
    try:
        response = client.chat.completions.create(
            model=TARGET_MODEL,
            messages=[{"role": "user", "content": user_content}],
            stream=False # 汇总阶段建议不使用 stream，直接获取完整结果进行保存
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error consolidating {bucket_name}: {e}")
        import time
        time.sleep(5)
        return ""

def main():
    for file_name in STAGE1_FILES:
        bucket_name = file_name.replace("analysis_", "").replace(".txt", "")
        print(f"\n>>> Starting Second Stage Consolidation for: {bucket_name}")
        
        blocks = parse_blocks(file_name)
        if not blocks:
            print(f"No content found for {bucket_name}. Skipping.")
            continue
            
        print(f"Found {len(blocks)} batch reports in {file_name}. Splitting into chunks...")
        
        # 分批处理，防止单个 Master Call 的输入太大
        master_summaries = []
        for i in range(0, len(blocks), SUMMARIZE_CHUNK_SIZE):
            chunk = blocks[i : i + SUMMARIZE_CHUNK_SIZE]
            print(f"  - Summarizing chunk {i//SUMMARIZE_CHUNK_SIZE + 1}...")
            summary = summarize_blocks(bucket_name, chunk)
            master_summaries.append(summary)
            middle_file_path = os.path.join(f"CHUNK_{bucket_name}_{i//SUMMARIZE_CHUNK_SIZE}.txt")
            with open(middle_file_path, "w", encoding='utf-8') as mf:
                mf.write(summary)
            
        # # 将局部汇总合并成最终的 Master Report
        # final_master_file = f"MASTER_REPORT_{bucket_name}.txt"
        # with open(final_master_file, "w", encoding='utf-8') as f:
        #     f.write(f"=== FINAL MASTER REPORT: {bucket_name} ===\n\n")
        #     # 如果有多个局部汇总，再进行最后一次合并
        #     if len(master_summaries) > 1:
        #         print(f"  - Finalizing master report for {bucket_name}...")
        #         final_output = summarize_blocks(bucket_name, master_summaries)
        #         f.write(final_output)
        #     else:
        #         f.write(master_summaries[0])
                
        # print(f"Done! Master report saved to {final_master_file}")

if __name__ == "__main__":
    main()