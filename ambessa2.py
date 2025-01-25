import subprocess
import time
import json
import os
from rich.console import Console
from rich.spinner import Spinner
from pentestgpt.utils.chatgpt import ChatGPT
from pentestgpt.config.chat_config import ChatGPTConfig
from prompts.prompt_class_v2 import PentestGPTPrompt  # Import the prompt class
from pentestgpt.utils.APIs.module_import import dynamic_import
import re

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
        Execute a shell command and return its output.
        """
        self.console.print(f"Executing command: {command}", style="bold magenta")
        try:
            # process = subprocess.run(
            #     command, shell=True, text=True, capture_output=True
            # )
            # output = process.stdout.strip()
            # error = process.stderr.strip()
            # return output, error
            print("Command executed")
            return None
        except Exception as e:
            return None, str(e)

    def start_conversation(self):
        """
        Start the penetration testing conversation loop.
        """
        # Initial prompt to GPT using the task_description and the target details
        initial_prompt = (
            f"{self.prompts.task_description}\n\n"
            f"Target IP: {self.target_ip}\n"
            f"Description: {self.target_description}\n"
            f"{self.prompts.first_todo}"
        )
        response = self.send_to_gpt(initial_prompt)

        while True:
            try:
                # Get the command from GPT's response
                # command = response.strip()
                # Regular expression to extract text between backticks
                command = re.findall(r'`(.*?)`', response)
                print("The Response is ", response)
                print("The Command is ", command)
                input()
                if command.lower() in ["exit", "quit", "stop"]:
                    self.console.print("Conversation ended by GPT.", style="bold red")
                    break

                # Execute the command and get results
                output, error = self.execute_command(command)
                if output:
                    self.console.print(f"Command Output: {output}", style="bold green")
                if error:
                    self.console.print(f"Command Error: {error}", style="bold red")

                # Prepare results to send back to GPT using the process_results prompt
                result_summary = (
                    f"{self.prompts.process_results}\n"
                    f"Command: {command}\n"
                    f"Output:\n{output or 'No output.'}\n"
                    f"Error:\n{error or 'No error.'}\n"
                )
                # Send results back to GPT
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
