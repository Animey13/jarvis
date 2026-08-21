"""
JARVIS Core Intelligence Layer Module.

Provides the primary intelligence orchestrator (`JarvisCore`) that manages
conversation context memory, persistent fact retrieval, system prompt rules,
tool execution decision-making, asynchronous LLM execution, latency tracking,
plugin manager integration, and graceful fallback handling for JARVIS.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from config.config import Settings
from llm.base import BaseLLMClient
from llm.ollama import OllamaClient
from memory.manager import MemoryManager
from plugins.manager import PluginManager
from tools.registry import ToolRegistry
from tools.system_tools import (
    CalculatorTool,
    DateTimeTool,
    ForgetMemoryTool,
    ListFilesTool,
    QueryMemoryTool,
    ReadFileTool,
    RememberTool,
    RestrictedCommandTool,
    SystemStatusTool,
)

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT: str = (
    "You are JARVIS, a local personal AI assistant. "
    "Provide short, concise, and natural spoken responses suitable for voice interaction. "
    "Do not use markdown formatting, bullet points, or verbose technical explanations unless requested. "
    "Acknowledge commands naturally and politely."
)

DEFAULT_FALLBACK_RESPONSE: str = "I'm sorry, I am currently unable to reach my local language model."


class JarvisCore:
    """
    Dedicated JARVIS Core Intelligence Orchestrator.
    Manages short-term conversation context, persistent memory retrieval, system prompts,
    tool & plugin execution decisions, LLM invocations, latency tracking, and fail-safe fallbacks.
    """

    def __init__(
        self,
        settings: Settings,
        llm_client: Optional[BaseLLMClient] = None,
        tool_registry: Optional[ToolRegistry] = None,
        memory_manager: Optional[MemoryManager] = None,
        plugin_manager: Optional[PluginManager] = None,
        max_context_length: int = 10,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        fallback_response: str = DEFAULT_FALLBACK_RESPONSE,
    ) -> None:
        """
        Initializes the JARVIS Core Intelligence orchestrator.
        """
        self.settings: Settings = settings
        self.max_context_length: int = max_context_length
        self.system_prompt: str = system_prompt
        self.fallback_response: str = fallback_response

        # Memory Manager Initialization
        if memory_manager is not None:
            self.memory_manager: MemoryManager = memory_manager
        else:
            logger.info("Initializing default MemoryManager in JarvisCore...")
            self.memory_manager = MemoryManager(max_short_term_turns=max_context_length)

        # LLM Client Initialization
        if llm_client is not None:
            self.llm_client: BaseLLMClient = llm_client
        else:
            logger.info("Initializing default OllamaClient in JarvisCore...")
            self.llm_client = OllamaClient(
                model_name=self.settings.llm.model,
                api_base=self.settings.llm.api_base,
                timeout=self.settings.llm.timeout,
            )

        # Tool Registry Initialization
        if tool_registry is not None:
            self.tool_registry: ToolRegistry = tool_registry
        else:
            logger.info("Initializing default ToolRegistry in JarvisCore...")
            self.tool_registry = ToolRegistry()
            self.tool_registry.register_tool(DateTimeTool())
            self.tool_registry.register_tool(CalculatorTool())
            self.tool_registry.register_tool(SystemStatusTool())
            self.tool_registry.register_tool(ListFilesTool())
            self.tool_registry.register_tool(ReadFileTool())
            self.tool_registry.register_tool(RestrictedCommandTool())
            self.tool_registry.register_tool(RememberTool(memory_manager=self.memory_manager))
            self.tool_registry.register_tool(QueryMemoryTool(memory_manager=self.memory_manager))
            self.tool_registry.register_tool(ForgetMemoryTool(memory_manager=self.memory_manager))

        # Plugin Manager Initialization & Bridge
        if plugin_manager is not None:
            self.plugin_manager: PluginManager = plugin_manager
            self.plugin_manager.tool_registry = self.tool_registry
            self.plugin_manager.sync_tools_with_registry()
        else:
            logger.info("Initializing default PluginManager in JarvisCore...")
            plugins_config = getattr(settings, "plugins", {})
            cfg_dict = {}
            if hasattr(plugins_config, "__dict__"):
                cfg_dict = plugins_config.__dict__
            elif isinstance(plugins_config, dict):
                cfg_dict = plugins_config

            self.plugin_manager = PluginManager(
                tool_registry=self.tool_registry,
                config=cfg_dict
            )

    @property
    def history(self) -> List[Any]:
        return self.memory_manager.get_short_term_history(limit=self.max_context_length)

    def add_turn(self, role: str, content: str) -> None:
        self.memory_manager.add_short_term_turn(role, content)

    def clear_context(self) -> None:
        self.memory_manager.clear_short_term()

    def build_prompt(self, user_text: str) -> str:
        prompt_parts: List[str] = []

        relevant_memories = self.memory_manager.retrieve(user_text, limit=3)
        if relevant_memories:
            prompt_parts.append("Relevant Persistent Facts & Preferences:")
            for rec in relevant_memories:
                prompt_parts.append(f"- {rec.get('key')}: {rec.get('value')}")
            prompt_parts.append("")

        short_history = self.memory_manager.get_short_term_history(limit=self.max_context_length)
        if short_history:
            prompt_parts.append("Recent conversation history:")
            for turn in short_history:
                role_label = str(turn.get("role", "")).upper()
                prompt_parts.append(f"{role_label}: {turn.get('content', '')}")
            prompt_parts.append("")

        prompt_parts.append(f"USER: {user_text}")
        return "\n".join(prompt_parts)

    def build_system_prompt(self) -> str:
        tools_desc = self.tool_registry.get_tools_prompt_description()
        return f"{self.system_prompt}\n\n{tools_desc}"

    async def respond(self, user_text: str) -> str:
        if not user_text or not str(user_text).strip():
            logger.warning("JarvisCore received empty user text input.")
            return "I didn't hear anything. How can I help you?"

        clean_input = str(user_text).strip()
        logger.info("JarvisCore received command: '%s'", clean_input)

        full_prompt = self.build_prompt(clean_input)
        effective_system_prompt = self.build_system_prompt()
        start_time = time.time()

        logger.info(
            "JarvisCore starting LLM request [Provider: %s, Model: %s, API: %s, Timeout: %.1fs]...",
            self.settings.llm.provider,
            self.llm_client.model_name,
            self.llm_client.api_base,
            self.llm_client.timeout,
        )

        try:
            response_text = await self.llm_client.generate(
                prompt=full_prompt, system_prompt=effective_system_prompt
            )
            elapsed_time = time.time() - start_time

            if not response_text or not response_text.strip():
                logger.warning("LLM request completed in %.2fs but yielded empty response text.", elapsed_time)
                return self.fallback_response

            clean_response = response_text.strip()
            logger.info(
                "LLM primary response generated in %.2fs (~%d chars): '%s'",
                elapsed_time,
                len(clean_response),
                clean_response,
            )

            # Check for tool / plugin execution decision tag
            tool_call = self.tool_registry.parse_tool_call(clean_response)
            if tool_call:
                tool_name, tool_args = tool_call
                logger.info("Tool/Plugin decision detected -> Name: '%s', Arguments: %s", tool_name, tool_args)

                try:
                    from web.state import event_bus, web_state
                    event_bus.publish("tool_start", data={"name": tool_name, "args": tool_args})
                except Exception:
                    pass

                exec_res = await self.tool_registry.execute_tool(tool_name, **tool_args)

                try:
                    from web.state import event_bus, web_state
                    event_bus.publish("tool_complete", data={"name": tool_name, "result": exec_res})
                    web_state.record_tool_execution(
                        name=tool_name,
                        args=tool_args,
                        status=exec_res.get("status", "completed"),
                        result_summary=str(exec_res.get("result", exec_res.get("error", "")))[:100]
                    )
                except Exception:
                    pass

                follow_up_prompt = (
                    f"{full_prompt}\n\n"
                    f"[Tool Execution Output for '{tool_name}']:\n"
                    f"{json.dumps(exec_res, indent=2)}\n\n"
                    "Please answer the user's original request naturally incorporating this real-time system output."
                )

                try:
                    synth_start = time.time()
                    clean_response = await self.llm_client.generate(
                        prompt=follow_up_prompt, system_prompt=self.system_prompt
                    )
                    clean_response = clean_response.strip() if clean_response else str(exec_res)
                    synth_elapsed = time.time() - synth_start
                    logger.info("LLM synthesis completed in %.2fs: '%s'", synth_elapsed, clean_response)
                except Exception as synth_err:
                    logger.warning("Follow-up LLM tool synthesis failed: %s. Using raw tool output.", synth_err)
                    clean_response = f"I executed {tool_name} and received: {exec_res}"

            self.add_turn("user", clean_input)
            self.add_turn("assistant", clean_response)

            return clean_response

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error("LLM request failed after %.2fs with error: %s", elapsed_time, e, exc_info=True)
            return self.fallback_response
