import subprocess
import time
import json
import os
from rich.console import Console
from rich.spinner import Spinner
from pentestgpt.utils.old_chatgpt import ChatGPT
from pentestgpt.config.chat_config import ChatGPTConfig
from prompts.prompt_class_v2 import PentestGPTPrompt  # Import the prompt class
from pentestgpt.utils.APIs.module_import import dynamic_import
import re
import multiprocessing

def command_select(input_list):
    """
    Selects the element with the longest character length from a list.
    
    Args:
        input_list (list): A list of strings to analyze.
    
    Returns:
        str: The string with the longest character length.
        None: If the list is empty.
    """
    if not input_list:  # Check if the list is empty
        return None
    return max(input_list, key=len)  # Use max() with key=len to find the longest element


class SimplifiedPentestGPT:
    def __init__(self, target_ip, target_description, log_dir="logs"):
        self.target_ip = target_ip
        self.target_description = target_description
        self.console = Console()
        self.spinner = Spinner("dots", "Processing")
        self.chatgpt = ChatGPT(ChatGPTConfig)
        self.conversation_id = None  # Conversation ID for GPT
        self.history = []
        self.log_dir = log_dir
        self.prompts = PentestGPTPrompt()  # Instantiate the prompts
        reasoning_model="gpt-4-turbo"
        parsing_model="gpt-4-turbo"
        os.makedirs(log_dir, exist_ok=True)

        self.console.print(f"Target IP: {target_ip}", style="bold green")
        self.console.print(f"Target Description: {target_description}", style="bold green")

        use_langfuse_logging=False
        
        # reasoning_model_object = dynamic_import(
        #     reasoning_model, self.log_dir, use_langfuse_logging=use_langfuse_logging
        # )
        # generation_model_object = dynamic_import(
        #     reasoning_model, self.log_dir, use_langfuse_logging=use_langfuse_logging
        # )
        # parsing_model_object = dynamic_import(
        #     parsing_model, self.log_dir, use_langfuse_logging=use_langfuse_logging
        # )


        # Initialize conversation
        self.initialize_conversation()




    def initialize_conversation(self):
        """
        Initialize a new conversation with GPT using the reasoning_session_init prompt.
        """
        self.console.print("Initializing conversation with GPT...", style="bold blue")
        try:
            _, self.conversation_id = self.chatgpt.send_new_message(
                self.prompts.reasoning_session_init
            )
            self.console.print(f"Conversation initialized: {self.conversation_id}", style="bold green")
        except Exception as e:
            self.console.print(f"Failed to initialize conversation: {str(e)}", style="bold red")
            raise e

    def send_to_gpt(self, prompt):
        """
        Send a prompt to GPT and get the response.
        """
        #self.console.print(f"Sending to GPT: {prompt}", style="bold blue")
        try:
            with self.console.status("[bold green] Waiting for GPT response..."):
                response = self.chatgpt.send_message(prompt, self.conversation_id)
            self.history.append({"user": prompt, "gpt": response})
            self.console.print(f"GPT Response: {response}", style="bold yellow")
            return response
        except Exception as e:
            self.console.print(f"Error while communicating with GPT: {str(e)}", style="bold red")
            raise e

    def execute_command(self, command):
        """
        Executes a command using subprocess and displays the output in real-time.
        
        Args:
            command (list): The command to execute as a list of arguments.
                            Example: ["ls", "-l"]
        Returns:
            tuple: A tuple containing the standard output and standard error (stdout, stderr).
        """
        #command = ["ping", self.target_ip, "-c", "4"]
        try:
            # Open the subprocess
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            stdout_lines = []  # To collect the standard output
            stderr_lines = []  # To collect the error output

            # Stream the output
            for line in process.stdout:
                print(line, end="")  # Print each line as it is received
                stdout_lines.append(line)  # Collect the output

            # Wait for the process to complete
            process.wait()

            # If the process failed, collect error output
            if process.returncode != 0:
                print("\nError output:")
                for line in process.stderr:
                    print(line, end="")
                    stderr_lines.append(line)

            # Combine stdout and stderr
            stdout = ''.join(stdout_lines)
            stderr = ''.join(stderr_lines)

            return stdout, stderr

        except FileNotFoundError:
            print("Error: Command not found. Please check the command and try again.")
            return None, None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None, None

    def validate_command(self, command: list[str]) -> list[str]:
        """
        Validate a command (as a list) to ensure it includes necessary flags to prevent indefinite execution.
        Adjusts commands like 'ping', 'tail', 'yes', 'watch', and 'nmap' to ensure safety.

        Args:
            command (list[str]): The command and its arguments as a list.

        Returns:
            list[str]: The validated and adjusted command.
        """
        if not command or not isinstance(command, list):
            return command  # Return as is if the command is empty or not a list

        # Command-specific validations
        if command[0] == "ping":
            # Ensure '-c 6' is included
            if '-c' in command:
                c_index = command.index('-c')
                if c_index + 1 < len(command) and command[c_index + 1].isdigit():
                    pass  # '-c' flag is valid
                else:
                    # Fix '-c' flag if it's present but invalid
                    if c_index + 1 < len(command):
                        command[c_index + 1] = '6'
            else:
                # Add '-c 6' if it's missing
                command.insert(1, '-c')
                command.insert(2, '6')

        elif command[0] == "tail":
            # Ensure '-n 100' or similar is included to limit the output
            if '-n' in command:
                n_index = command.index('-n')
                if n_index + 1 < len(command) and command[n_index + 1].isdigit():
                    pass  # '-n' flag is valid
                else:
                    # Fix '-n' flag if it's present but invalid
                    if n_index + 1 < len(command):
                        command[n_index + 1] = '100'
            else:
                # Add '-n 100' if it's missing
                command.insert(1, '-n')
                command.insert(2, '100')

        elif command[0] == "yes":
            # Prevent the 'yes' command from running indefinitely
            command = ["timeout", "5s"] + command

        elif command[0] == "watch":
            # Ensure a proper interval is set with '-n'
            if '-n' in command:
                n_index = command.index('-n')
                if n_index + 1 < len(command) and command[n_index + 1].isdigit():
                    pass  # '-n' flag is valid
                else:
                    # Fix '-n' flag if it's present but invalid
                    if n_index + 1 < len(command):
                        command[n_index + 1] = '2'
            else:
                # Add '-n 2' (2-second interval) if it's missing
                command.insert(1, '-n')
                command.insert(2, '2')

        elif command[0] == "nmap":
            # Check if there's a .txt result file with 'nmap' in its name in the current directory
            result_files = [f for f in os.listdir('.') if f.endswith('.txt') and 'nmap' in f]
            if result_files:
                # Change command to 'cat <first_result_file>'
                command = ["cat", result_files[0]]

        return command
    
    

    def execute_bruteforce(self, command):
        """
        Function to execute a brute force command in a separate process.
        """
        try:
            print(f"Executing brute force command: {command}")
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            stdout, stderr = process.communicate()
            return stdout, stderr
        except Exception as e:
            return None, str(e)


    def is_bruteforce_command(self, command):
        """
        Check if a command is a brute force command.
        """
        brute_keywords = ["hydra", "medusa", "brute", "bruteforce"]
        return any(keyword in command for keyword in brute_keywords)


    def start_conversation(self):
        """
        Start the penetration testing conversation loop.
        """
        initial_prompt = (
            f"{self.prompts.task_description}\n\n"
            f"Target IP: {self.target_ip}\n"
            f"Description: {self.target_description}\n"
            f"{self.prompts.first_todo}"
        )
        response = self.send_to_gpt(initial_prompt)
        brute_process = None  # To track the brute force process
        brute_result = None   # To store brute force results

        while True:
            try:
                # Extract commands from GPT's response
                commands = re.findall(r'```(.*?)```|`([^`]*)`', response, re.DOTALL)
                commands = [cmd[0] or cmd[1] for cmd in commands]

                if not commands:
                    self.console.print("No valid command found in response. Asking GPT for suggestions.", style="bold yellow")
                    suggestion_prompt = f"Response received:\n{response}\nPlease suggest useful commands for this situation."
                    response = self.send_to_gpt(suggestion_prompt)
                    continue

                command = commands[0].strip()
                if not command:
                    self.console.print("Empty command found. Asking GPT for suggestions.", style="bold yellow")
                    suggestion_prompt = f"Response received:\n{response}\nPlease suggest useful commands for this situation."
                    response = self.send_to_gpt(suggestion_prompt)
                    continue

                command = self.validate_command(command)

                if self.is_bruteforce_command(command):
                    # Handle brute force command in a separate process
                    self.console.print(f"Brute force command detected: {command}. Running in a separate process.", style="bold yellow")
                    brute_process = multiprocessing.Process(target=self.execute_bruteforce, args=(command.split(),))
                    brute_process.start()

                    # Inform GPT about the running brute force and ask for another command
                    response = self.send_to_gpt("A brute force task is running. Please suggest another command to execute.")
                    continue

                if brute_process and brute_process.is_alive():
                    self.console.print("Brute force process is still running.", style="bold blue")

                elif brute_process and not brute_process.is_alive():
                    if brute_result is None:  # Fetch result only once
                        brute_stdout, brute_stderr = self.execute_bruteforce(command.split())
                        brute_result = f"Brute force completed. Output:\n{brute_stdout}\nError:\n{brute_stderr}"
                        self.console.print(brute_result, style="bold green")

                print("Command is:", command)

                user_input = input()
                if command.lower() in ["exit", "quit", "stop"] or user_input in ["exit", "quit", "stop"]:
                    self.console.print("Conversation ended by user.", style="bold red")
                    break

                output, error = self.execute_command(command.split())
                if output:
                    self.console.print(f"Command Output: {output}", style="bold green")
                if error:
                    self.console.print(f"Command Error: {error}", style="bold red")

                result_summary = (
                    f"{self.prompts.process_results}\n"
                    f"Command: `{command}`\n"
                    f"Output:\n{output or 'No output.'}\n"
                    f"Error:\n{error or 'No error.'}\n"
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
    target_ip = "192.168.1.1"  # Example IP
    target_description = "A sample target for penetration testing."
    pentest = SimplifiedPentestGPT(target_ip, target_description)
    pentest.start_conversation()
    pentest.save_history()
