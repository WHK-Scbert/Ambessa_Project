import os
import re
import subprocess
import time
import json
import shutil
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

    def validate_command(self, command):
        """
        Validate a command for safety and usability.
        """
        if not command or not isinstance(command, list):
            return False, "Invalid command format."

        # Check if the command exists on the system
        if shutil.which(command[0]) is None:
            return False, f"Command not found: {command[0]}"

        return True, "Command is valid."

    def command_simplified(self, command):
        """
        Simplify commands to avoid potential errors or infinite loops.
        """
        if not command or not isinstance(command, list):
            return command

        # Replace `nmap` with `cat` if nmap results exist
        if command[0] == "nmap":
            existing_files = [f for f in os.listdir(".") if "nmap" in f and f.endswith(".txt")]
            if existing_files:
                self.console.print(f"[bold yellow]Found existing nmap result: {existing_files[0]}[/bold yellow]")
                return ["cat", existing_files[0]]

        # Ensure `ping` includes `-c 6`
        if command[0] == "ping":
            if "-c" not in command:
                command.extend(["-c", "6"])

        # Ensure `tail` includes `-n 100` to limit output
        if command[0] == "tail":
            if "-n" not in command:
                command.extend(["-n", "100"])

        # Ensure `watch` includes `-n 2` to set a safe refresh interval
        if command[0] == "watch":
            if "-n" not in command:
                command.extend(["-n", "2"])

        # Add `timeout` to `yes` to prevent infinite loops
        if command[0] == "yes":
            return ["timeout", "5s"] + command

        # Default to returning the command unmodified
        return command


    def execute_command_in_new_window(self, command):
        """
        Execute a command in a new terminal window to display results in real time.
        """
        try:
            # Simplify the command before execution
            command = self.command_simplified(command)

            self.console.print(f"[bold blue]About to execute command: {' '.join(command)}[/bold blue]")

            # Spawn a new terminal window for the command
            terminal_command = ["x-terminal-emulator", "-e"] + command  # Adjust for your terminal
            process = subprocess.Popen(terminal_command)
            process.wait()

        except FileNotFoundError:
            self.console.print("[bold red]Error: Terminal emulator not found. Install x-terminal-emulator or adjust the terminal command.[/bold red]")
        except Exception as e:
            self.console.print(f"Error executing command in new window: {str(e)}", style="bold red")

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
                    response = self.send_to_gpt(self.prompts.ask_todo)
                    continue

                command = commands[0].strip().split()
                is_valid, validation_message = self.validate_command(command)
                if not is_valid:
                    self.console.print(f"[bold red]Command validation failed: {validation_message}[/bold red]")
                    response = self.send_to_gpt(f"Command validation failed: {validation_message}. Suggest next steps.")
                    continue

                self.execute_command_in_new_window(command)

                # Send command results to GPT (placeholder example)
                result_summary = f"{self.prompts.process_results}\nCommand: {' '.join(command)}\nOutput: Executed in a separate window.\n"
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
