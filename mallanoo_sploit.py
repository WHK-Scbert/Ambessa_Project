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

    def extract_command_from_response(self, response):
        """
        Extract and sanitize the command from GPT's response.
        """
        # Extract content inside triple backticks
        matches = re.findall(r'```(?:bash)?\s*(.*?)\s*```', response, re.DOTALL)
        if matches:
            # Take the first match and split it into arguments
            command = matches[0].strip().split()
            return command
        return None



    def execute_command_in_new_window(self, command):
        """
        Execute a command in a new terminal window to display results in real time.
        Captures and returns the output for `cat` commands.
        """
        try:
            # Simplify the command before execution
            command = self.command_simplified(command)

            if not command:
                self.console.print("[bold yellow]Command was skipped due to invalid or missing arguments.[/bold yellow]")
                return None

            self.console.print(f"[bold blue]About to execute command: {' '.join(command)}[/bold blue]")

            # If the command is `cat`, capture the output directly
            if command[0] == "cat":
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()

                if process.returncode != 0:
                    self.console.print(f"[bold red]Error executing `cat`: {stderr}[/bold red]")
                    return None

                self.console.print(f"[bold green]Captured output from `cat`: {stdout}[/bold green]")
                return stdout

            # For other commands, execute them in a new terminal window
            terminal_command = ["x-terminal-emulator", "-e"] + command  # Adjust for your terminal
            process = subprocess.Popen(terminal_command)
            process.wait()

            if process.returncode != 0:
                self.console.print(f"[bold red]Command failed: {' '.join(command)}[/bold red]")
                return None

        except FileNotFoundError:
            self.console.print("[bold red]Error: Terminal emulator not found. Install x-terminal-emulator or adjust the terminal command.[/bold red]")
            return None
        except Exception as e:
            self.console.print(f"[bold red]Unexpected error executing command: {str(e)}[/bold red]")
            return None


    def handle_failed_command(self, error_message):
        """
        Handle a failed command by asking GPT for a new command.
        """
        self.console.print("[bold yellow]Asking GPT for a new command due to failure...[/bold yellow]")
        try:
            response = self.send_to_gpt(f"{self.prompts.ask_todo}\n\nCommand failure details:\n{error_message}")
            self.console.print("[bold green]Received new suggestions from GPT.[/bold green]")
        except Exception as e:
            self.console.print(f"[bold red]Error while asking GPT for a new command: {str(e)}[/bold red]")

    def extract_command_with_gpt(self, response):
        """
        Use ChatGPT to extract and suggest a command from the given response.
        """
        try:
            self.console.print("[bold blue]Asking GPT to suggest a command from its own response...[/bold blue]")

            # Craft a prompt asking GPT to extract a single command
            prompt = (
                "Below is the output of your previous response. Please extract the command that should be executed. "
                "If there are multiple commands, suggest only the most relevant one. Enclose your response in triple backticks.\n\n"
                f"{response}"
            )

            # Send the prompt to GPT
            extracted_command_response = self.send_to_gpt(prompt)

            if not extracted_command_response:
                self.console.print("[bold yellow]GPT did not return a response.[/bold yellow]")
                return None

            # Extract the suggested command from the GPT response
            matches = re.findall(r'```(?:bash)?\s*(.*?)\s*```', extracted_command_response, re.DOTALL)
            if matches:
                command = matches[0].strip().split()
                self.console.print(f"[bold green]Command extracted: {' '.join(command)}[/bold green]")
                return command
            else:
                self.console.print("[bold yellow]GPT did not suggest a valid command.[/bold yellow]")
                return None
        except Exception as e:
            self.console.print(f"[bold red]Error extracting command with GPT: {str(e)}[/bold red]")
            return None

    def start_conversation(self):
        """
        Start the main penetration testing workflow with error handling for commands.
        Handles captured output, retries, and gracefully exits if retries fail.
        """
        initial_prompt = (
            f"{self.prompts.task_description}\n\n"
            f"Target IP: {self.target_ip}\n"
            f"Description: {self.target_description}\n"
            f"{self.prompts.first_todo}"
        )
        response = self.send_to_gpt(initial_prompt)

        retry_count = 0
        max_retries = 5  # Limit the number of retries to prevent infinite loops

        while True:
            try:
                # Use GPT to extract a command from the response
                command = self.extract_command_with_gpt(response)

                if not command:
                    retry_count += 1
                    if retry_count > max_retries:
                        self.console.print("[bold red]Max retries reached. Exiting conversation.[/bold red]")
                        break

                    self.console.print(f"[bold yellow]Retrying... ({retry_count}/{max_retries})[/bold yellow]")
                    response = self.send_to_gpt(
                        "GPT did not suggest a valid command. Please analyze the previous task and suggest the next steps."
                    )
                    continue

                # Reset retry count if a valid command is found
                retry_count = 0

                is_valid, validation_message = self.validate_command(command)
                if not is_valid:
                    self.console.print(f"[bold red]Command validation failed: {validation_message}[/bold red]")
                    response = self.send_to_gpt(f"Command validation failed: {validation_message}. Suggest next steps.")
                    continue

                # Special handling for `cat` commands
                if command[0] == "cat":
                    self.console.print("[bold blue]Executing `cat` command and capturing output...[/bold blue]")
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stdout, stderr = process.communicate()

                    if process.returncode != 0:
                        self.console.print(f"[bold red]Error executing `cat`: {stderr}[/bold red]")
                        response = self.send_to_gpt(f"Error executing `cat` command: {stderr}. Suggest next steps.")
                        continue

                    # Send the output of `cat` to GPT
                    self.console.print("[bold green]Captured output from `cat` command. Sending to GPT...[/bold green]")
                    response = self.send_to_gpt(
                        f"{self.prompts.process_results}\nCommand: {' '.join(command)}\nOutput:\n{stdout}"
                    )
                    continue

                # For non-`cat` commands, execute in a new terminal window
                self.execute_command_in_new_window(command)

                # Send command execution status to GPT
                result_summary = f"{self.prompts.process_results}\nCommand: {' '.join(command)}\nOutput: Executed in a separate window.\n"
                response = self.send_to_gpt(result_summary)

            except KeyboardInterrupt:
                self.console.print("Interrupted by user. Exiting.", style="bold red")
                break
            except Exception as e:
                self.console.print(f"[bold red]Error: {str(e)}[/bold red]")
                response = self.send_to_gpt(f"An error occurred: {str(e)}. Please suggest a way to continue.")
                retry_count += 1
                if retry_count > max_retries:
                    self.console.print("[bold red]Max retries reached due to repeated errors. Exiting conversation.[/bold red]")
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
