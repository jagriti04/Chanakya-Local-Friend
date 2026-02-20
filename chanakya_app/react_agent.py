import re
import json
from typing import Union, Any
from langchain_core.agents import AgentAction, AgentFinish
from langchain_classic.agents import AgentExecutor, AgentOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_classic.agents.format_scratchpad import format_log_to_str
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
import scripts.config as config
from .app_setup import app
from . import tool_loader
from .chat_history import get_chat_history

REACT_AGENT_PROMPT_TEMPLATE_STR = """
{dynamic_intro_and_memories}

You have access to the following tools:
{tools}

IMPORTANT: You may wrap your entire response for a turn in a single pair of <think>...</think> tags. Inside these tags, you MUST strictly follow the Thought/Action/Final Answer format. Do not use <think> tags inside your Thought, Action, or Final Answer text itself.

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

class CustomReActSingleInputOutputParser(AgentOutputParser):
    def _parse_json_input(self, tool_input_str: str) -> Any:
        tool_input_str_stripped = tool_input_str.strip()
        if tool_input_str_stripped.startswith(("{", "[")) and tool_input_str_stripped.endswith(("}", "]")):
            try:
                parsed_json = json.loads(tool_input_str_stripped)
                return parsed_json
            except json.JSONDecodeError:
                pass
        return tool_input_str_stripped

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        app.logger.debug(f"ReAct Parser (LLM always wraps in <think>): Raw text received:\n'''{text}'''")

        original_cleaned_text = text.strip() # Keep original for logging/error messages

        # --- Stage 1: Handle potential outer <think>...</think> wrapper ---
        content_to_parse = original_cleaned_text
        outer_think_match = re.fullmatch(r"<think>(.*?)</think>", original_cleaned_text, flags=re.DOTALL | re.IGNORECASE)

        if outer_think_match:
            app.logger.debug("ReAct Parser: Found and stripped outer <think>...</think> block.")
            content_to_parse = outer_think_match.group(1).strip() # Parse what's inside
        else:
            app.logger.debug("ReAct Parser: No single outer <think>...</think> block found. Parsing original text.")
            # This parser assumes the PRIMARY ReAct structure is *inside* the optional outer <think> block.

        app.logger.debug(f"ReAct Parser: Content to parse for Action/Final Answer:\n'''{content_to_parse}'''")

        # --- Stage 2: Check if the content_to_parse (after outer think removal) is empty or just the word "<think>" ---
        if not content_to_parse: # Empty after stripping outer <think>
            error_msg = f"LLM output was an empty <think></think> block or became empty after processing. Original: `{original_cleaned_text}`."
            app.logger.error(f"ReAct Parser Error: {error_msg}")
            raise OutputParserException(error_msg, observation=error_msg, llm_output=original_cleaned_text)

        if content_to_parse.lower() == "<think>": # Literal "<think>" string inside the outer wrapper (or as whole output)
            error_msg = f"LLM output (or content within outer <think> block) was just the word '<think>'. Original: `{original_cleaned_text}`. An Action or Final Answer is required."
            app.logger.error(f"ReAct Parser Error: {error_msg}")
            raise OutputParserException(error_msg, observation=error_msg, llm_output=original_cleaned_text)

        # --- Stage 3: Parse for Action or Final Answer within content_to_parse ---
        # Now, remove any *remaining* (potentially inner) <think> blocks from content_to_parse
        # before trying to find Action/Final Answer keywords.
        # This is if the LLM does <think><think>Thought:...</think></think> or <think>Thought: <think>detail</think></think>
        content_for_keywords = re.sub(r"<think>.*?</think>", "", content_to_parse, flags=re.DOTALL | re.IGNORECASE).strip()
        app.logger.debug(f"ReAct Parser: Content for keyword search (after all think removals):\n'''{content_for_keywords}'''")

        if not content_for_keywords: # If removing inner thinks also makes it empty
            error_msg = f"After processing all <think> blocks, no content remained for Action/Final Answer. Original: `{original_cleaned_text}`."
            app.logger.error(f"ReAct Parser Error: {error_msg}")
            raise OutputParserException(error_msg, observation=error_msg, llm_output=original_cleaned_text)


        includes_answer = "Final Answer:" in content_for_keywords
        includes_action = "Action:" in content_for_keywords
        app.logger.debug(f"ReAct Parser: Keyword search: includes_answer={includes_answer}, includes_action={includes_action}")

        if includes_answer and includes_action:
            idx_answer = content_for_keywords.rfind("Final Answer:")
            idx_action = content_for_keywords.rfind("Action:")
            if idx_answer > idx_action:
                app.logger.info("ReAct Parser: Both Action and Final Answer found; Final Answer is later, choosing Final Answer.")
                _, answer_content = content_for_keywords.rsplit("Final Answer:", 1)
                return AgentFinish({"output": answer_content.strip()}, original_cleaned_text) # Log original
            else:
                app.logger.warning(f"ReAct Parser: Both Action and Final Answer found; Action is later. Attempting Action. Original: `{original_cleaned_text}`")
                # Fall through

        if includes_action:
            # Use content_for_keywords for regex matching, as <think> tags around action parts are now removed.
            action_input_pattern_text = content_for_keywords
            if "Action Input:" not in action_input_pattern_text:
                error_msg = f"'Action:' found but no 'Action Input:' field. (Keyword Search Text): `{action_input_pattern_text}`. Original: `{original_cleaned_text}`"
                app.logger.error(f"ReAct Parser Error: {error_msg}")
                raise OutputParserException(error_msg, observation=error_msg, llm_output=original_cleaned_text)

            action_input_stop_keywords = r"\nThought:|\nAction:|\nFinal Answer:|$"
            patterns_to_try = [
                rf"(?:Thought\s*:.*?\n)?Action\s*:(.*?)\nAction\s*Input\s*:[\s]*(.*?)(?={action_input_stop_keywords})",
                rf"Action\s*:(.*?)\s+Action\s*Input\s*:[\s]*(.*?)(?={action_input_stop_keywords})"
            ]
            match = None
            for pattern_str in patterns_to_try:
                match = re.search(pattern_str, action_input_pattern_text, re.DOTALL | re.IGNORECASE)
                if match: break

            if not match:
                error_msg = f"Could not parse 'Action:' and 'Action Input:' with regex (Keyword Search Text): `{action_input_pattern_text}`. Original: `{original_cleaned_text}`"
                app.logger.error(f"ReAct Parser Error: {error_msg}")
                raise OutputParserException(error_msg, observation=error_msg, llm_output=original_cleaned_text)

            action_tool = match.group(1).strip()
            action_input_str_raw = match.group(2).strip()
            action_input_str_for_json = action_input_str_raw
            if (action_input_str_raw.startswith('"') and action_input_str_raw.endswith('"')) or \
               (action_input_str_raw.startswith("'") and action_input_str_raw.endswith("'")):
                temp_unquoted = action_input_str_raw[1:-1]
                if (temp_unquoted.strip().startswith('{') and temp_unquoted.strip().endswith('}')) or \
                   (temp_unquoted.strip().startswith('[') and temp_unquoted.strip().endswith(']')):
                    action_input_str_for_json = temp_unquoted.replace('\\"', '"') if action_input_str_raw.startswith('"') else temp_unquoted.replace("\\'", "'")

            tool_input = self._parse_json_input(action_input_str_for_json)
            app.logger.info(f"ReAct Parser: Parsed Action: {action_tool}, Input: {tool_input}")
            return AgentAction(action_tool, tool_input, original_cleaned_text) # Log original

        if includes_answer:
            _, answer_content = content_for_keywords.rsplit("Final Answer:", 1)
            app.logger.info(f"ReAct Parser: Parsed Final Answer: {answer_content.strip()}")
            return AgentFinish({"output": answer_content.strip()}, original_cleaned_text) # Log original

        # If no Action or Final Answer was found in content_for_keywords,
        # but content_for_keywords is not empty, it's likely a plain statement from the LLM.
        if content_for_keywords:
            app.logger.info(f"ReAct Parser: No Action or Final Answer keywords found. Returning remaining content as output: '{content_for_keywords}'. Original: `{original_cleaned_text}`")
            return AgentFinish({"output": content_for_keywords}, original_cleaned_text)

        # This should ideally not be reached if the above checks are comprehensive
        final_error_msg = f"ReAct Parser: Unable to parse LLM output into Action or Final Answer after all processing. Original: `{original_cleaned_text}`"
        app.logger.error(final_error_msg)
        raise OutputParserException(final_error_msg, observation=final_error_msg, llm_output=original_cleaned_text)

    @property
    def _type(self) -> str: return "custom_react_parser_chanakya_v_outer_think"


def get_chanakya_react_agent_with_history():
    provider = config.LLM_PROVIDER.lower()
    app.logger.info(f"Configuring LLM with provider: {provider}")

    if provider == 'ollama':
        current_chanakya_llm = ChatOllama(
            model=config.LLM_MODEL_NAME,
            base_url=config.LLM_ENDPOINT,
            num_ctx=config.LLM_NUM_CTX,
            temperature=0.1,
            stop=["\nObservation:", "\n\tObservation:"]
        )
    elif provider == 'openai' or provider == 'lmstudio':
        current_chanakya_llm = ChatOpenAI(
            model=config.LLM_MODEL_NAME,
            base_url=config.LLM_ENDPOINT,
            api_key=config.LLM_API_KEY or "NA", # Some servers need a dummy key
            temperature=0.1,
            max_tokens=1500, # A reasonable default
            stop=["\nObservation:", "\n\tObservation:"]
        )
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {config.LLM_PROVIDER}")

    current_tools = tool_loader.CACHED_MCP_TOOLS
    if not current_tools:
        app.logger.warning("Creating Chanakya ReAct agent with NO tools available!")

    tool_instructions = ""
    try:
        # Assuming the app is run from the project root directory
        with open("tool_specific_instructions.txt", "r", encoding="utf-8") as f:
            tool_instructions = f.read().strip()
        app.logger.info("Successfully loaded tool-specific instructions.")
    except FileNotFoundError:
        app.logger.warning("'tool_specific_instructions.txt' not found. Proceeding without tool instructions.")
    except Exception as e:
        app.logger.error(f"Error loading tool-specific instructions: {e}")

    react_prompt_template = PromptTemplate.from_template(
        template=REACT_AGENT_PROMPT_TEMPLATE_STR,
        partial_variables={"tool_instructions": tool_instructions}
    )

    agent_chain = (
        RunnablePassthrough.assign(
            agent_scratchpad=lambda x: format_log_to_str(x.get("intermediate_steps", []))
        )
        | react_prompt_template
        | current_chanakya_llm
        | CustomReActSingleInputOutputParser()
    )

    agent_executor = AgentExecutor(
        agent=agent_chain,
        tools=current_tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10,
        return_intermediate_steps=True
    )

    return RunnableWithMessageHistory(
        agent_executor,
        get_chat_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )
