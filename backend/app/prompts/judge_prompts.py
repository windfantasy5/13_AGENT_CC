"""
Judge Prompts - Evaluation prompts for quality assessment
"""

# Retrieval Quality Judge Prompt
RETRIEVAL_QUALITY_PROMPT = """你是一个专业的信息相关性评判专家。

请评估以下检索到的参考资料与用户问题的相关性。

用户问题：
{query}

参考资料：
{context}

评判标准：
1. 参考资料是否包含回答问题所需的关键信息
2. 参考资料的内容是否与问题主题直接相关
3. 参考资料是否足够详细和准确

请按以下JSON格式输出评判结果：
{{
    "score": <0-10的整数评分>,
    "reason": "<评判理由，说明为什么给出这个分数>",
    "is_relevant": <true或false，评分>=6为true>
}}

评分说明：
- 9-10分：高度相关，包含完整准确的答案
- 7-8分：相关性强，包含大部分所需信息
- 5-6分：部分相关，包含少量有用信息
- 3-4分：相关性弱，信息不够充分
- 0-2分：不相关，无法回答问题

请直接输出JSON，不要添加其他内容。"""

# Consistency Checker Prompt
CONSISTENCY_CHECKER_PROMPT = """你是一个专业的信息一致性检查专家。

请检查以下多个参考资料之间是否存在矛盾或冲突的信息。

参考资料列表：
{contexts}

检查要点：
1. 不同资料对同一事实的描述是否一致
2. 数据、日期、数字等关键信息是否冲突
3. 结论或观点是否相互矛盾

请按以下JSON格式输出检查结果：
{{
    "has_conflict": <true或false>,
    "conflicts": [
        {{
            "description": "<矛盾描述>",
            "sources": ["<资料1索引>", "<资料2索引>"]
        }}
    ],
    "summary": "<总体一致性评价>"
}}

如果没有发现矛盾，conflicts数组为空。

请直接输出JSON，不要添加其他内容。"""

# Answer Quality Judge Prompt
ANSWER_QUALITY_PROMPT = """你是一个专业的答案质量评判专家。

请评估AI生成的答案质量。

用户问题：
{query}

参考资料：
{context}

AI生成的答案：
{answer}

评判标准：
1. 答案是否准确回答了用户的问题
2. 答案是否基于参考资料，没有编造信息
3. 答案是否逻辑清晰、表达流畅
4. 答案是否完整，没有遗漏关键信息
5. 答案是否客观中立，没有偏见

请按以下JSON格式输出评判结果：
{{
    "score": <0-10的整数评分>,
    "reason": "<评判理由>",
    "is_acceptable": <true或false，评分>=7为true>,
    "issues": [
        "<问题1>",
        "<问题2>"
    ]
}}

评分说明：
- 9-10分：优秀，准确完整且表达清晰
- 7-8分：良好，基本准确但可能有小瑕疵
- 5-6分：一般，部分准确但存在明显问题
- 3-4分：较差，准确性或完整性不足
- 0-2分：很差，严重错误或偏离主题

如果没有发现问题，issues数组为空。

请直接输出JSON，不要添加其他内容。"""
