# 一些失败尝试

我试图从官方benchmark中筛选出top-5模型的作答，并分成四类（TP, TN, FP, FN）让大模型总结经验，但随机测了几个题发现没有任何效果:(
*TP: 实际对，模型答对， TN: 实际错，模型答对， FP: 实际对，模型答错， FN: 实际错，模型答错*

## 文件说明
- `data.jsonl`: 筛选出的top-5模型的作答，只含hard题集，默认reasoning
- `distill.py`, `distill_2.py`, `final.py`: 数据太多，分了三阶段蒸馏
- `stage1/`: 第一阶段的结果
- `stage2/`: 第二阶段的结果
- `FINAL_*`: 最终的提示词（只是长度不同）