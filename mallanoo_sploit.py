import subprocess
import time
import json
import os
import re
from rich.console import Console
from pentestgpt.utils.chatgpt import ChatGPT
from pentestgpt.config.chat_config import ChatGPTConfig
from prompts.prompt_class_v2 import PentestGPTPrompt


class MallanooSploit:
    def __init__(self, target_ip, target_description, log_dir="logs"):
        self.target_ip = target_ip
        self.target_description = target_description
        self.console = Console()
        self.chatgpt = ChatGPT(ChatGPTConfig)
        self.conversation_id = None
        self.history = []
        self.log_dir = log_dir
        self.prompts = PentestGPTPrompt()
        os.makedirs(log_dir, exist_ok=True)

        self.console.print(f"Target IP: {target_ip}", style="bold green")
        self.console.print(f"Target Description: {target_description}", style="bold green")

        self.initialize_conversation()

    def initialize_conversation(self):
        """
        Initialize a new conversation with GPT using prompts.
        """
        self.console.print("Initializing conversation with GPT...", style="bold blue")
        try:
            init_response, self.conversation_id = self.chatgpt.send_new_message(
                self.prompts.generation_session_init
            )
            self.history.append({"user": self.prompts.generation_session_init, "gpt": init_response})

            reasoning_response = self.chatgpt.send_message(self.prompts.reasoning_session_init, self.conversation_id)
            self.history.append({"user": self.prompts.reasoning_session_init, "gpt": reasoning_response})

            self.console.print(f"Conversation initialized: {self.conversation_id}", style="bold green")
        except Exception as e:
            self.console.print(f"Failed to initialize conversation: {str(e)}", style="bold red")
            raise e

    def send_to_gpt(self, prompt):
        """
        Send a prompt to GPT, including the history of the conversation, and get the response.
        """
        conversation_context = "\n".join(
            f"User: {entry['user']}\nGPT: {entry['gpt']}" for entry in self.history
        )
        full_prompt = f"{conversation_context}\nUser: {prompt}\nGPT:"
        try:
            response = self.chatgpt.send_message(full_prompt, self.conversation_id)
            self.history.append({"user": prompt, "gpt": response})
            self.console.print(f"GPT Response: {response}", style="bold yellow")
            return response
        except Exception as e:
            self.console.print(f"Error while communicating with GPT: {str(e)}", style="bold red")
            raise e

    def execute_command(self, command):
        """
        Executes a command using subprocess and captures the output.
        """
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                self.console.print(f"Command failed with error: {stderr}", style="bold red")
            return stdout, stderr
        except Exception as e:
            self.console.print(f"Error executing command: {str(e)}", style="bold red")
            return None, None

    def validate_command(self, command):
        """
        Validate and adjust commands for safety and usability.
        """
        if not command or not isinstance(command, list):
            return command
        if command[0] == "ping" and "-c" not in command:
            command.extend(["-c", "4"])
        return command

    def is_bruteforce_command(self, command):
        """
        Check if a command is related to brute force operations.
        """
        brute_keywords = ["hydra", "medusa", "brute", "bruteforce"]
        return any(keyword in command for keyword in brute_keywords)

    def start_conversation(self):
        """
        Start the main penetration testing workflow.
        """
        initial_prompt = (
            f"{self.prompts.task_description}\n\n"
            f"Target IP: {self.target_ip}\n"
            f"Description: {self.target_description}\n"
            f"{self.prompts.first_todo}"
        )
        response = self.send_to_gpt(initial_prompt)

        while True:
            try:
                commands = re.findall(r'```(.*?)```|`([^`]*)`', response, re.DOTALL)
                commands = [cmd[0] or cmd[1] for cmd in commands]

                if not commands:
                    self.console.print("No valid command found in response.", style="bold yellow")
                    response = self.send_to_gpt("No valid command. Suggest next steps.")
                    continue

                command = self.validate_command(commands[0].split())
                if self.is_bruteforce_command(command):
                    self.console.print("Executing brute force command...", style="bold yellow")
                    brute_stdout, brute_stderr = self.execute_command(command)
                    self.console.print(f"Brute Force Output: {brute_stdout}", style="bold green")
                    response = self.send_to_gpt("Brute force completed. Suggest next steps.")
                    continue

                stdout, stderr = self.execute_command(command)
                result_summary = (
                    f"{self.prompts.process_results}\n"
                    f"Command: {command}\n"
                    f"Output:\n{stdout or 'No output.'}\n"
                    f"Error:\n{stderr or 'No error.'}\n"
                )
                response = self.send_to_gpt(result_summary)
            except KeyboardInterrupt:
                self.console.print("Interrupted by user. Exiting.", style="bold red")
                break
            except Exception as e:
                self.console.print(f"Error: {str(e)}", style="bold red")
                break

    def save_history(self):
        """
        Save the conversation history to a log file.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.log_dir, f"pentestGPT_log_{timestamp}.json")
        with open(log_file, "w") as f:
            json.dump(self.history, f, indent=2)
        self.console.print(f"History saved to {log_file}", style="bold green")


if __name__ == "__main__":
    target_ip = "192.168.1.1"
    target_description = "A sample target for penetration testing."
    pentest = MallanooSploit(target_ip, target_description)
    pentest.start_conversation()
    pentest.save_history()
