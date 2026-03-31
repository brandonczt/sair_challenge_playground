import os
from openai import OpenAI

# --- 配置区 ---
client = OpenAI(
    api_key="", 
    base_url="https://api.linkapi.ai/v1"
)

# 第二阶段生成的 Master Report 文件名
MASTER_FILES = {
    "TP": "CHUNK_TP.txt",
    "TN": "CHUNK_TN.txt",
    "FP": "CHUNK_FP.txt",
    "FN": "CHUNK_FN.txt"
}

TARGET_MODEL = "[次]gemini-3.1-pro-preview"
OUTPUT_PROMPT_FILE = "FINAL_COMPETITION_PROMPT.md"

# --- 提示词：2.2 跨类别最终合成 (Final Synthesis) ---
FINAL_SYNTHESIS_PROMPT = """
**Task: High-Density System Prompt Engineering**
**Input:** Master reports from four performance quadrants (TP: Successes, TN: Refutations, FP: Hallucinations, FN: Failures).

**Goal:** Create a specialized System Prompt for an AI agent to solve Equational Theory problems with maximum accuracy and minimum hallucination.

**Constraints:** 
1. **Length:** The final prompt should be around 1500 words.
2. **Focus:** Prioritize the "How-to" (from TP) and "Safety Constraints" (from FP).

**Structure of the Final Prompt (Required):**
1. **Role Definition:** (Expert in Abstract Algebra and Term Rewriting).
2. **Pre-Check Phase:** Instructions on how to analyze the equation structure before proving.
3. **Step-by-Step Reasoning Protocol:** A mandatory logical flow .
4. **Negative Constraints (The 'Anti-Hallucination' Wall):** Explicitly list the illegal moves identified in the FP/FN reports.
5. **Refutation Trigger:** Clear conditions for when to switch from proving to searching for a counter-model.

**Instructions for Synthesis:**
- Transform the *insights* from the Master Reports into *imperative commands* (e.g., Change "Models often fail at nested brackets" to "Always verify variable mapping inside nested parentheses after every substitution step").
- Use markdown for clarity.
"""

def load_master_reports():
    """读取所有类别的 Master Reports"""
    combined_content = ""
    for category, file_path in MASTER_FILES.items():
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                combined_content += f"\n\n### {category} MASTER REPORT ###\n{content}"
        else:
            print(f"Warning: {file_path} not found. Skipping {category}.")
    return combined_content

def generate_final_prompt():
    print(">>> Loading Master Reports for Final Synthesis...")
    all_masters = load_master_reports()
    
    if not all_masters:
        print("Error: No Master Reports found. Please run Stage 2 first.")
        return

    print(f">>> Sending to {TARGET_MODEL} for Final Synthesis...")
    
    user_message = f"{FINAL_SYNTHESIS_PROMPT}\n\n--- MASTER DATA START ---\n{all_masters}\n--- MASTER DATA END ---"

    try:
        response = client.chat.completions.create(
            model=TARGET_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert prompt engineer specializing in mathematical reasoning distillation."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3, # 较低温度以获得更严谨的结构
            stream=False
        )
        
        final_prompt = response.choices[0].message.content
        
        # 将生成的最终提示词保存到本地
        with open(OUTPUT_PROMPT_FILE, "w", encoding="utf-8") as f:
            f.write(final_prompt)
            
        print(f"\nSUCCESS! The competition-ready System Prompt has been saved to: {OUTPUT_PROMPT_FILE}")
        print("-" * 50)
        print("Preview of the generated prompt:")
        print(final_prompt[:500] + "...") # 预览前500字
        
    except Exception as e:
        print(f"Error during final synthesis: {e}")

if __name__ == "__main__":
    generate_final_prompt()