"""
Query refinement chain using a smaller LLM.

Refines user queries before passing to the main agent for better results.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from .. import config
from ..web.app_setup import app

from ..prompts.prompts import QUERY_REFINEMENT_TEMPLATE_STR

query_refinement_template_str = QUERY_REFINEMENT_TEMPLATE_STR
query_refinement_prompt_template_obj = ChatPromptTemplate.from_template(
    query_refinement_template_str
)


def get_query_refinement_chain():
    """Return a configured LLM chain for query refinement, or None if disabled."""
    provider = config.LLM_PROVIDER.lower()
    app.logger.info(f"Configuring Query Refinement LLM with provider: {provider}")

    if not config.LLM_MODEL_NAME_SMALL or not config.LLM_ENDPOINT_SMALL:
        app.logger.warning(
            "Small LLM not configured, query refinement will be disabled."
        )
        return None

    if provider == "ollama":
        query_ref_llm = ChatOllama(
            model=config.LLM_MODEL_NAME_SMALL,
            base_url=config.LLM_ENDPOINT_SMALL,
            num_ctx=config.LLM_NUM_CTX_SMALL,
            temperature=0,
        )
    elif provider == "openai" or provider == "lmstudio":
        query_ref_llm = ChatOpenAI(
            model=config.LLM_MODEL_NAME_SMALL,
            base_url=config.LLM_ENDPOINT_SMALL,
            api_key=config.LLM_API_KEY or "NA",
            temperature=0,
            max_tokens=50,  # Keywords should be short
        )
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER for query refinement: {config.LLM_PROVIDER}"
        )

    return query_refinement_prompt_template_obj | query_ref_llm
