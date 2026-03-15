"""
Prompt templates for the Chanakya chatbot.

Contains REACT_AGENT_PROMPT_TEMPLATE_STR and QUERY_REFINEMENT_TEMPLATE_STR.
"""

REACT_AGENT_PROMPT_TEMPLATE_STR = """
{dynamic_intro_and_memories}

You have access to the following tools:
{tools}

IMPORTANT: You may wrap your entire response for a turn in a tags. Inside these tags, you MUST strictly follow the Thought/Action/Final Answer format. Do not use <think> tags inside your Thought, Action, or Final Answer text itself.

To use a tool, you MUST use the following format, producing only ONE action block per turn:
Thought: [Your reasoning for the current action. Focus on a single step.]
Action: [The name of the tool you want to use from the list: {tool_names}]
Action Input: [The actual data or JSON object required by the chosen tool. See tool descriptions for expected arguments. For example, if a tool expects a JSON object with a "query" key, you would provide: {{"query": "your search term"}}]

After the system provides an "Observation:" with the result of your action, you will continue with a new "Thought:" and then either another "Action:" block for the next step, or a "Final Answer:".

If you have the final answer, or if the user is just chatting, use the format:
Thought: [Your reasoning that you have the final answer or that no tool is needed.]
Final Answer: [your response to the user]

**Error Handling Guidance:**
- If an Observation contains a parsing error, your PREVIOUS response was malformed. Your NEW response MUST start with a "Thought:" explaining your correction, followed by a valid "Action:" block or "Final Answer:".
- If an Observation is a tool error, start your NEW response with "Thought:" to analyze it, then proceed with a corrected "Action:" or a "Final Answer:".

Tool specific instructions: {tool_instructions}

ALWAYS PROVIDE THE CORRECT ARGUMENTS AS REQUIRED BY THE TOOL. Refer to the tool descriptions for argument details.
Begin!

PREVIOUS CONVERSATION:
{chat_history}

Current User Request: {input}
Thought:{agent_scratchpad}
"""

QUERY_REFINEMENT_TEMPLATE_STR = """
You are an expert at converting user questions into a set of relevant keywords suitable for retrieving information from a knowledge base. Don't generate any keyword if the User's question is not relarted to any memory or doesn't need memories to answer.
Your last response: {ai_response}
User question: {user_question}
Generate up to 10 distinct (less is better), concise keywords that capture the main concepts. Remove articles and unnecessary words. Separate the keywords with commas.
Keywords:
"""
