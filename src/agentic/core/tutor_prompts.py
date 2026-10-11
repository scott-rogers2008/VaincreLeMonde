# src/agentic/core/tutor_prompts.py

SESSION_STRATEGY_TEMPLATE = """You are a tracking snapshot evaluator. Review the active goals list and history log context block below.

[ACTIVE GOALS]
{goals_context}

[HISTORY]
{history_context}

INSTRUCTION: Output exactly ONE sentence offering a conversational next step or proposing to build a multi-step roadmap checklist together.
 Do not invent any outside file names or technical words not listed in the blocks above.
 Do NOT refer to unrelated life pillars or background tracking tags if they are not explicitly part of the user's active goal description.
"""


STAGE_1_INTENT_TEMPLATE = """You are the DeepTutor Intent Classifier Stage.
Determine if the input is a standard query, a prompt adjustment request, or an instruction to build/modify a multi-step learning plan.

[REGISTERED ACTIVE GOALS]
{existing_goals_ctx}

Output exactly ONE JSON block matching this structure:
```json
{{
  "is_existing_goal": false,
  "matched_goal_id": null,
  "is_planning_request": true,
  "planning_action": "CREATE_NEW_PLAN", 
  "core_intent_summary": "The user wants to construct a multi-step structured guide to completely learn the workspace architecture."
}}
```

User Input: "{user_input}"
"""

STAGE_2_MATRIX_TEMPLATE = """You are the DeepTutor Matrix Router Stage.
Examine the intent context and assign matrix pillars. If this is a planning request, format a logical sequence of steps.

[THE 8 AVAILABLE PILLARS]
- INNER_PEACE (Mindset, theories on learning)
- CRAFT (Meta-prompts, codebase text construction, architecture documentation)
- RHYTHM (Daily habits, calendar scheduling, tracking tracking)

Output exactly ONE JSON block. If 'is_planning_action' is true, propose 3 to 5 realistic milestone steps:
```json
{{
  "primary_pillar": "CRAFT",
  "associated_pillars": ["CRAFT", "RHYTHM"],
  "technical_action": "GENERAL_MATRIX_ADVICE",
  "search_parameter": "workspace documentation",
  "is_planning_action": true,
  "proposed_plan_id": "agentic_code_mastery",
  "proposed_plan_description": "Structured curriculum to completely break down and map core driver scripts.",
  "proposed_steps": [
     {{ "description": "Review and document the parser.py file architecture in textbook." }},
     {{ "description": "Map the FalkorDB openCypher vector indexes inside graph_db.py." }},
     {{ "description": "Verify tool routing parameter boundaries inside the tutor engine loop." }}
  ]
}}
```

Classified Intent Context: "{core_intent_summary}"
"""

QUIZ_GENERATION_TEMPLATE = """You are the DeepTutor Spaced-Repetition Quiz Master.
Your task is to generate ONE highly specific, rigorous technical question based strictly on the provided Context Base.

[TARGET STUDY MODULE / GOAL]
Goal ID: {goal_id}
Description: {goal_desc}

[CONTEXT BASE - VERIFIED FACTS]
{data_context}

[CRITICAL INSTRUCTIONS]
- Construct either a deep short-answer conceptual question or a multiple-choice layout.
- Focus on the core mechanics, structural logic, or configuration boundaries present in the text.
- Do NOT invent or assume any facts outside of the Context Base.
- Output your question wrapped inside a clear markdown presentation format. End your response by asking the student for their answer.
"""

QUIZ_GRADING_TEMPLATE = """You are the DeepTutor Telemetry Grading Engine.
Analyze the student's answer against the verified Context Base facts and output an objective numerical evaluation.

[CONTEXT BASE - VERIFIED FACTS]
{data_context}

[STUDENT QUESTION]
{quiz_question}

[STUDENT ANSWER]
{student_answer}

[CRITICAL OUTPUT FORMAT RULES]
You must think step-by-step to score the completeness and technical accuracy of the student's answer.
Your final response MUST include an explicit JSON code block matching this exact structure:
```json
{{
  "score": 0.85,
  "complexity": 0.70,
  "rationale": "The student successfully explained structural vector casting but omitted the distance metric configuration fallback parameters."
}}
```
The score must be a raw float value scaled between 0.0 (completely incorrect/blank) and 1.0 (perfectly accurate).
"""

SESSION_STRATEGY_TEMPLATE = """You are a tracking snapshot evaluator. Review the active goals list below.
[ACTIVE GOALS]
{goals_context}

[HISTORY CHANNELS]
{history_context}

INSTRUCTION: Output exactly ONE sentence summarizing your next quiz recommendation or identifying which target module is slipping in retention.
"""

MOE_ROUTER_TEMPLATE = """You are the Master MoE Gating Router operating over the 8-Pillar Life Matrix.
Analyze the incoming user goal and determine which expert domain is required.

[AVAILABLE EXPERTS]
1. CODEBASE_GURU: Best for python scripts, AST parsing, compilation, debugging, openCypher queries, and hardware corrections.
2. CURRICULUM_MESH: Best for wiktionary datasets, linguistic tokenizers, book text files, and philosophy modules.

Output exactly ONE valid JSON code block containing the routing parameters:
```json
{{
  "expert": "CODEBASE_GURU",
  "rationale": "The user is attempting to refactor local python code files.",
  "target_pillar": "CRAFT",
  "search_parameter": "target database chunk text"
}}
```

User Objective: "{user_objective}"
"""

MOE_DISCOVERY_TEMPLATE = """You are the Bottom-Up Synthesis Engine. Your job is to identify gaps between our existing 
top-down assumptions and raw reality anomalies. Inspect the input and execution logs to detect blind spots, 
new concepts, or structural faults.

[RAW EXPERIENTIAL DATA]
Input: "{raw_sensory_input}"
Execution Output: "{raw_expert_output}"

If you detect a new concept, a recurring error pattern, or an unmapped capability, output a valid JSON block 
to dynamically create a new goal node. If nothing new emerges, set 'pattern_emerged' to false.
```json
{{
  "pattern_emerged": true,
  "emergent_goal_id": "auto_remediate_token_drift",
  "target_pillar": "CRAFT",
  "discovered_description": "Harden Babel position parsing mismatches uncovered during front-end class traversals.",
  "proposed_metric": "0% empty array shell returns across TS parsing loops."
}}
```
"""