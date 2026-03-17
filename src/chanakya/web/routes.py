"""
Flask routes for the Chanakya chatbot.

Handles /, /chat, /record, /play_response, /memory endpoints.
Uses async/await for long-running operations.
"""

import asyncio
import base64
import datetime
import os
import tempfile
import time

from flask import jsonify, redirect, render_template, request, url_for
from langchain_core.agents import AgentAction
from langchain_core.tools import ToolException

from .. import config
from ..core.memory_management import (
    add_memory,
    delete_memory,
    list_all_memories,
    retrieve_relevant_memories,
)
from ..core.query_refinement import get_query_refinement_chain
from ..core.react_agent import get_chanakya_react_agent_with_history
from ..services import tool_loader
from ..services.audio_service import get_stt, get_tts
from ..utils import utils as utils_module  # to modify last_ai_response
from ..utils.utils import get_plain_text_content
from .app_setup import app
from .client_activity import (
    COUNT_FILE,
    SAVE_INTERVAL,
    active_clients,
    remove_inactive_clients,
    update_client_activity,
)


@app.route("/")
def index():
    update_client_activity(request.remote_addr)
    return render_template(
        "index_full_chat.html",
        timestamp=datetime.datetime.now().timestamp(),
        wake_word=config.WAKE_WORD,
    )


def background_thread():
    last_save_time = time.time()
    while True:
        current_time = time.time()
        remove_inactive_clients()
        if current_time - last_save_time >= SAVE_INTERVAL:
            try:
                with open(COUNT_FILE, "w") as f:
                    f.write(str(len(active_clients)))
            except IOError as e:
                app.logger.error(f"Error writing count file: {e}")
            last_save_time = current_time
        time.sleep(1)


@app.route("/chat", methods=["POST"])
async def chat():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    app.logger.info(f"--- ASYNC /CHAT (Loop: {id(loop)}) User: '{request.form['message']}' ---")

    update_client_activity(request.remote_addr)
    user_message = request.form["message"]

    if not user_message or not user_message.strip():
        return jsonify({"response": "Please provide a message."})
    try:
        current_query_refinement_chain = get_query_refinement_chain()
        refined_keywords = ""
        if current_query_refinement_chain is not None:
            refined_keywords_output = await asyncio.wait_for(
                current_query_refinement_chain.ainvoke(
                    {
                        "user_question": user_message,
                        "ai_response": utils_module.last_ai_response,
                    }
                ),
                timeout=15,
            )
            refined_keywords = get_plain_text_content(refined_keywords_output)
        else:
            app.logger.warning("Query refinement chain is None, skipping query refinement.")

        memory_search_query = user_message
        if refined_keywords and refined_keywords.lower() not in ["none", ""]:
            memory_search_query += " " + refined_keywords
        relevant_memories = retrieve_relevant_memories(memory_search_query)

        current_dt_str = datetime.datetime.now().strftime("%Y-%m-%d, %I:%M:%S %p")
        dynamic_intro = f"""You are a conversational AI voice assistant named {config.WAKE_WORD}. Created by Dr. Rishabh Bajpai.
Your primary mode of interaction with the user is through voice (a phone call). Craft responses to be clear, concise, and natural-sounding.
Use shorter sentences and standard punctuation for natural pauses. Avoid complex sentence structures, markdown, or emojis.
Keep responses brief and conversational.
Do not repeat responses or ask unnecessary follow-up questions.
When you are asked something, try to understand the full intent. If a complex task requires multiple steps or tools, break it down into a sequence of actions and use the tools as needed for each step to achieve the final goal. Avoid asking the user for small details if they can be inferred or handled by tools.
Current date and time: {current_dt_str}"""

        memories_str = ""
        if relevant_memories:
            memories_str = (
                "\n\nRelevant Memories (use if applicable for context or to avoid repeating work):\n"
                + "\n".join([f"- Date: {dt}, Memory: {mem}" for dt, mem in relevant_memories])
            )

        dynamic_intro_and_memories_content = dynamic_intro + memories_str

        current_react_agent_with_history = get_chanakya_react_agent_with_history()

        app.logger.info(f"CHAT - Invoking Chanakya ReAct agent (ASYNC) input: '{user_message}'")
        response_payload = await asyncio.wait_for(
            current_react_agent_with_history.ainvoke(
                {
                    "input": user_message,
                    "dynamic_intro_and_memories": dynamic_intro_and_memories_content,
                    "tools": tool_loader.mcp_tool_descriptions_for_llm,
                    "tool_names": tool_loader.mcp_tool_names_for_llm,
                },
                config={"configurable": {"session_id": "global_shared_session"}},
            ),
            timeout=20,
        )
        app.logger.info(
            f"CHAT - Raw Chanakya ReAct AgentExecutor async response: {response_payload}"
        )

        used_tools_in_turn = set()
        if "intermediate_steps" in response_payload and response_payload["intermediate_steps"]:
            for step in response_payload["intermediate_steps"]:
                if isinstance(step, tuple) and len(step) > 0 and isinstance(step[0], AgentAction):
                    used_tools_in_turn.add(step[0].tool)
            if used_tools_in_turn:
                app.logger.info(f"CHAT - Tools used in this turn: {list(used_tools_in_turn)}")
            else:
                app.logger.info(
                    "CHAT - No tools were explicitly called in the intermediate steps for this turn."
                )
        else:
            app.logger.info(
                "CHAT - No intermediate_steps found in agent response (no tools called or not a ReAct agent)."
            )

        utils_module.last_ai_response = get_plain_text_content(response_payload)
        app.logger.info(f"CHAT - Final text response: {utils_module.last_ai_response}")

        return jsonify(
            {
                "response": utils_module.last_ai_response,
                "used_tools": list(used_tools_in_turn),
            }
        )
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            app.logger.error(f"EVENT LOOP CLOSED ERROR in /chat: {e}", exc_info=True)
            return jsonify({"response": "Internal server error: Event loop issue."}), 500
        else:
            app.logger.error(f"Runtime error in /chat: {e}", exc_info=True)
            return jsonify({"response": f"Sorry, a runtime error occurred: {e}"}), 500
    except ToolException as e:
        app.logger.warning(f"Tool error in /chat: {e}")
        return jsonify(
            {
                "response": f"I encountered an issue while using one of my tools: {str(e)}. Please try again or rephrase your request.",
                "used_tools": [],
            }
        )
    except Exception as e:
        app.logger.error(f"Error in /chat endpoint: {e}", exc_info=True)
        return jsonify({"response": "Sorry, I encountered an error processing your message."}), 500


@app.route("/record", methods=["POST"])
async def record():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    app.logger.info(f"--- ASYNC /RECORD (Loop: {id(loop)}) ---")

    update_client_activity(request.remote_addr)
    if "audio" not in request.files:
        return jsonify({"error": "No audio file part."}), 400
    audio_file_storage = request.files["audio"]
    if audio_file_storage.filename == "":
        return jsonify({"error": "No selected file."}), 400

    if audio_file_storage:
        temp_audio_file_path_stt = None
        try:
            audio_data = audio_file_storage.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_f:
                temp_f.write(audio_data)
                temp_audio_file_path_stt = temp_f.name

            transcription = get_stt().transcribe(temp_audio_file_path_stt)
            if transcription is None or not transcription.strip():
                return jsonify({"error": "Could not understand audio."}), 400
            app.logger.info(f"RECORD - Transcription: '{transcription}'")
            user_message = transcription

            current_query_refinement_chain = get_query_refinement_chain()
            refined_keywords = ""
            if current_query_refinement_chain is not None:
                refined_keywords_output = await asyncio.wait_for(
                    current_query_refinement_chain.ainvoke(
                        {
                            "user_question": user_message,
                            "ai_response": utils_module.last_ai_response,
                        }
                    ),
                    timeout=15,
                )
                refined_keywords = get_plain_text_content(refined_keywords_output)
            else:
                app.logger.warning("Query refinement chain is None in /record, skipping.")
            memory_search_query = transcription
            if refined_keywords and refined_keywords.lower() not in ["none", ""]:
                memory_search_query += " " + refined_keywords
            relevant_memories = retrieve_relevant_memories(memory_search_query)

            current_dt_str = datetime.datetime.now().strftime("%Y-%m-%d, %I:%M:%S %p")
            dynamic_intro = f"""You are a conversational AI voice assistant named {config.WAKE_WORD}. Created by Dr. Rishabh Bajpai.
Your primary mode of interaction with the user is through voice (a phone call). Craft responses to be clear, concise, and natural-sounding.
Use shorter sentences and standard punctuation for natural pauses. Avoid complex sentence structures, markdown, or emojis.
Keep responses brief and conversational.
Do not repeat responses or ask unnecessary follow-up questions.
When you are asked something, try to understand the full intent. If a complex task requires multiple steps or tools, break it down into a sequence of actions and use the tools as needed for each step to achieve the final goal. Avoid asking the user for small details if they can be inferred or handled by tools.
Current date and time: {current_dt_str}"""
            memories_str = ""
            if relevant_memories:
                memories_str = (
                    "\n\nRelevant Memories (use if applicable for context or to avoid repeating work):\n"
                    + "\n".join([f"- Date: {dt}, Memory: {mem}" for dt, mem in relevant_memories])
                )
            dynamic_intro_and_memories_content = dynamic_intro + memories_str

            current_react_agent_with_history = get_chanakya_react_agent_with_history()

            app.logger.info(
                f"RECORD - Invoking Chanakya ReAct agent (ASYNC) input: '{transcription}'"
            )
            response_payload = await asyncio.wait_for(
                current_react_agent_with_history.ainvoke(
                    {
                        "input": user_message,
                        "dynamic_intro_and_memories": dynamic_intro_and_memories_content,
                        "tools": tool_loader.mcp_tool_descriptions_for_llm,
                        "tool_names": tool_loader.mcp_tool_names_for_llm,
                    },
                    config={"configurable": {"session_id": "global_shared_session"}},
                ),
                timeout=20,
            )
            app.logger.info(
                f"RECORD - Raw Chanakya ReAct AgentExecutor async response: {response_payload}"
            )
            utils_module.last_ai_response = get_plain_text_content(response_payload)
            app.logger.info(f"RECORD - Final text response: {utils_module.last_ai_response}")

            used_tools_in_turn = set()
            if "intermediate_steps" in response_payload and response_payload["intermediate_steps"]:
                app.logger.info(
                    f"RECORD - Intermediate steps: {response_payload['intermediate_steps']}"
                )
                for step in response_payload["intermediate_steps"]:
                    if (
                        isinstance(step, tuple)
                        and len(step) > 0
                        and isinstance(step[0], AgentAction)
                    ):
                        used_tools_in_turn.add(step[0].tool)

            bot_speech_audio_data_url = None
            if utils_module.last_ai_response:
                tts_audio_bytes = get_tts().generate(utils_module.last_ai_response)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tts_f:
                    tts_f.write(tts_audio_bytes)
                    tts_audio_file_path_for_bot_response = tts_f.name
                if tts_audio_file_path_for_bot_response and os.path.exists(
                    tts_audio_file_path_for_bot_response
                ):
                    with open(tts_audio_file_path_for_bot_response, "rb") as f_audio:
                        audio_bytes = f_audio.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                    bot_speech_audio_data_url = f"data:audio/wav;base64,{audio_base64}"
                else:
                    app.logger.error("TTS failed in /record")
            return jsonify(
                {
                    "response": utils_module.last_ai_response,
                    "transcription": transcription,
                    "audio_data_url": bot_speech_audio_data_url,
                    "used_tools": list(used_tools_in_turn),
                }
            )
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                app.logger.error(f"EVENT LOOP CLOSED ERROR in /record: {e}", exc_info=True)
                return jsonify({"response": "Internal server error: Event loop issue."}), 500
            else:
                app.logger.error(f"Runtime error in /record: {e}", exc_info=True)
                return jsonify({"response": f"Sorry, a runtime error occurred: {e}"}), 500
        except ToolException as e:
            app.logger.warning(f"Tool error in /record: {e}")
            return jsonify(
                {
                    "response": f"I encountered an issue while using one of my tools: {str(e)}.",
                    "transcription": transcription,
                    "used_tools": [],
                }
            )
        except Exception as e:
            app.logger.error(f"Error processing /record: {e}", exc_info=True)
            return jsonify({"error": f"Server error: {str(e)}"}), 500
        finally:
            if temp_audio_file_path_stt and os.path.exists(temp_audio_file_path_stt):
                try:
                    os.remove(temp_audio_file_path_stt)
                except OSError:
                    pass
    return jsonify({"error": "Audio file not processed correctly."}), 400


@app.route("/play_response", methods=["POST"])
def play_response():
    update_client_activity(request.remote_addr)
    if utils_module.last_ai_response:
        try:
            tts_audio_bytes = get_tts().generate(utils_module.last_ai_response)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tts_f:
                tts_f.write(tts_audio_bytes)
                audio_file_path = tts_f.name
            if not audio_file_path or not os.path.exists(audio_file_path):
                return jsonify({"error": "TTS audio file not found or not created."}), 500
            with open(audio_file_path, "rb") as f_audio:
                audio_bytes = f_audio.read()
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            return jsonify({"audio_data_url": f"data:audio/wav;base64,{audio_base64}"})
        except Exception as e:
            app.logger.error(f"Error in /play_response: {e}", exc_info=True)
            return jsonify({"error": f"Server error: {str(e)}"}), 500
    return jsonify({"error": "No response available to play."})


@app.route("/memory")
def memory_page():
    """Renders the memory management page."""
    memories = list_all_memories()
    return render_template("manage_memory.html", memories=memories)


@app.route("/add-memory", methods=["POST"])
def add_memory_route():
    """Handles adding a new memory."""
    memory_text = request.form.get("memory_text")
    if memory_text:
        add_memory(memory_text)
    return redirect(url_for("memory_page"))


@app.route("/delete-memory", methods=["POST"])
def delete_memory_route():
    """Handles deleting a memory."""
    memory_id = request.form.get("memory_id")
    if memory_id:
        delete_memory(memory_id)
    return redirect(url_for("memory_page"))
