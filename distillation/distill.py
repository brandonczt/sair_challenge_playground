import json
import random
from openai import OpenAI

# --- 配置区 ---
client = OpenAI(
    api_key="", # 替换为你的 API Key
    base_url="https://api.linkapi.ai/v1",
    timeout=1000.0
)

DATA_PATH = "data.jsonl"
BATCH_SIZE = 10  # 每批处理的数据量，建议根据 response 长度调整（5-10条比较稳妥）
TARGET_MODEL = "[次]gemini-3.1-pro-preview"

# --- 提示词模板 (已留空，可填入之前建议的英文 Prompt) ---
BACKGROUND = """
**Background:** We are participating in the "Equational Theories" mathematics challenge. The task involves proving or disproving whether `equation1` implies `equation2` within a specific equational theory. We have a large dataset of model responses, including their reasoning, proofs, and counterexamples.
"""

PROMPTS = {
    "TP": """Task: Meta-Analysis of Successful Proofs (TP). 
**Goal:** Identify the most efficient derivation strategies and successful logical structures.
**Input:** A list of cases where the model correctly proved that `equation1` implies `equation2`.

**Analysis Requirements:**
1. **Axiom Application Patterns:** Look at the `response` field. Which specific algebraic transformations were most effective?
2. **Derivation Direction:** Did successful proofs typically move from LHS to RHS, or did they simplify both sides to a "Normal Form"?
3. **Intermediate Lemmas:** Identify if the models frequently derived "hidden" properties as stepping stones.
4. **Structural Heuristics:** How did the model break down complex nested terms? 

**Output:** Provide a "Prover's Manual" summarizing high-level strategies that characterize these successful proofs as many as possible.
""",
    "TN": """Task: Meta-Analysis of Correct Refutations (TN). 
**Goal:** Learn how to efficiently find counter-models and identify unprovable equations.

**Input:** A list of cases where the model correctly identified that `equation1` does NOT imply `equation2` by providing a counterexample.

**Analysis Requirements:**
1. **Counter-model Construction:** What size of sets (e.g., {0, 1} or {0, 1, 2}) were most common for counterexamples? How were the binary operations (`*`) defined?
2. **Inconsistency Detection:** How did the model realize early on that the proof was impossible? Did it look at term length, variable frequency, or parity?
3. **Search Heuristics:** What "Red Flags" in the equations triggered the search for a counterexample instead of a proof?

**Output:** Provide a "Skeptic’s Checklist" of signs that an equation is likely false and a recipe for constructing minimal counter-models as many as possible.
""",
    "FP": """Task: Meta-Analysis of Hallucinated Proofs (FP). 
**Goal:** Identify logical pitfalls and "fake" math steps to create negative constraints.

**Input:** A list of cases where the model claimed a proof existed (Answer: TRUE), but the judge ruled it FALSE (Correct: FALSE).

**Analysis Requirements:**
1. **Illegal Substitutions:** Where exactly did the model "cheat"? (e.g., replacing `x*y` with `y*x` when commutativity wasn't given).
2. **Circular Reasoning:** Identify instances where the model assumed the conclusion to prove the conclusion.
3. **Symbolic Overload:** Does the model lose track of variables in deeply nested equations? Identify the "Complexity Threshold" where logic breaks down.
4. **Notation Errors:** Did the model misinterpret the scope of parentheses?

**Output:** Provide a "Safety Warning List" of common hallucination patterns to avoid in the final System Prompt as many as possible.
""",
    "FN": """Task: Meta-Analysis of Failed Proof searches (FN). 
**Goal:** Understand why models "give up" or fail to find a valid proof.


**Input:** A list of cases where a proof exists, but the model concluded it was FALSE or failed to find it.

**Analysis Requirements:**
1. **Search Depth:** At what point did the model stop exploring? (e.g., after 5 steps, after 10 steps).
2. **Missing Links:** What "unobvious" substitution or axiom application did the model overlook?
3. **Local Optima:** Did the model get stuck in a loop of expanding and shrinking the same term without moving toward the goal?
4. **Complexity Bias:** Did the model prematurely give up because the target equation looked too different from the source?

**Output:** Provide a "Persistence Strategy" summarizing how the prompt should encourage the model to explore alternative "non-obvious" transformation paths.
"""
}

# --- 数据加载与分类 ---
def load_data(path):
    buckets = {"TP": [], "TN": [], "FP": [], "FN": []}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line.strip())
            # TP: 模型说对，实际对; TN: 模型说错，实际对(指模型判定不成立); 
            # FP: 模型说对，实际错; FN: 模型说错，实际错(指模型没找到证明)
            # 根据你之前的逻辑：answer是模型给出的结论，correct是判定这个结论是否正确
            ans = item.get("answer")
            cor = item.get("correct")
            
            if ans is True and cor is True: buckets["TP"].append(item)
            elif ans is False and cor is True: buckets["TN"].append(item)
            elif ans is True and cor is False: buckets["FP"].append(item)
            elif ans is False and cor is False: buckets["FN"].append(item)
            
    # 打乱每一类数据
    for key in buckets:
        random.shuffle(buckets[key])
    return buckets

def run_distillation(bucket_name, data_list):
    if not data_list:
        print(f"Skipping {bucket_name}: No data found.")
        return

    print(f"\n=== Processing {bucket_name} Bucket (Total: {len(data_list)}) ===")
    
    # 仅取前几批进行蒸馏，或者全量跑完
    for i in range(0, len(data_list), BATCH_SIZE):
        batch = data_list[i:i+BATCH_SIZE]
        
        # 精简发送给模型的数据量
        clean_batch = []
        for d in batch:
            clean_batch.append({
                "problem_id": d.get("problem_id"),
                "eq1": d.get("equation1"),
                "eq2": d.get("equation2"),
                "model_answer": d.get("answer"),
                "model_response": d.get("response") # 包含 Reasoning 和 Proof
            })

        user_content = f"{BACKGROUND}\n{PROMPTS[bucket_name]}\n\nData to analyze:\n{json.dumps(clean_batch, indent=2)}"
        
        try:
            print(f"--- Sending Batch {i//BATCH_SIZE + 1} ---")
            
            # --- 修改点 1: stream 改为 False ---
            response = client.chat.completions.create(
                model=TARGET_MODEL,
                messages=[{"role": "user", "content": user_content}],
                stream=False 
            )

            # --- 修改点 2: 直接获取完整内容 ---
            content = response.choices[0].message.content
            
            # 打印到屏幕看一眼
            print(content[:200] + "..." if len(content) > 200 else content)

            # 保存到本地
            with open(f"analysis_{bucket_name}.txt", "a", encoding='utf-8') as out_f:
                out_f.write(f"\n--- Batch {i//BATCH_SIZE + 1} Analysis ---\n")
                out_f.write(content)
                out_f.write("\n")

        except Exception as e:
            print(f"Error processing batch: {e}")
            import time
            time.sleep(5)

# --- 执行主程序 ---
if __name__ == "__main__":
    all_buckets = load_data(DATA_PATH)
    
    # 依次处理四个桶
    for bucket_type in ["FN"]:
        # 建议先处理 TP 和 FP，因为它们对 Proof 逻辑的提示词贡献最大
        run_distillation(bucket_type, all_buckets[bucket_type])

    print("\nStage 1 Distillation Complete. Results saved to analysis_*.txt files.")