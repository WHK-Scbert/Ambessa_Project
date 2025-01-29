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
import pexpect


class MallanooSploit:
    def __init__(self, target_ip, target_description, my_ip, log_dir="logs"):
        self.target_ip = target_ip
        self.target_description = target_description
        self.my_ip = my_ip
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
            if init_response:
                self.history.append({"user": self.prompts.generation_session_init, "gpt": init_response})
            else:
                self.console.print("[bold yellow]GPT did not provide an initialization response.[/bold yellow]")

            reasoning_response = self.chatgpt.send_message(self.prompts.reasoning_session_init, self.conversation_id)
            if reasoning_response:
                self.history.append({"user": self.prompts.reasoning_session_init, "gpt": reasoning_response})
            else:
                self.console.print("[bold yellow]GPT did not provide a reasoning response.[/bold yellow]")

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

            if response:  # Only append to history if response is valid
                self.history.append({"user": prompt, "gpt": response})
                self.console.print(f"GPT Response: {response}", style="bold yellow")
                return response
            else:
                self.console.print("[bold yellow]GPT returned an empty or None response.[/bold yellow]")
                return None

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

    def execute_command(self, command):
        """
        Execute a command directly within the application, handle password prompts or interactive prompts if necessary,
        and display results in real time. Captures and returns the output or error for further use.
        Includes a 1-minute timeout for the command execution.
        """
        try:
            # Simplify the command before execution
            command = self.command_simplified(command)

            if not command:
                self.console.print("[bold yellow]Command was skipped due to invalid or missing arguments.[/bold yellow]")
                return None

            self.console.print(f"[bold blue]About to execute command: {' '.join(command)}[/bold blue]")

            # Use pexpect to spawn the command
            process = pexpect.spawn(" ".join(command), timeout=60, encoding='utf-8')  # Set timeout to 60 seconds
            stdout_lines = []
            stderr_lines = []

            # Check if the command is `smbclient` and handle interactions
            is_smbclient = command[0] == "smbclient"

            # Monitor the process until it finishes
            finished = False
            while not finished:
                # Check if the process has reached EOF, timed out, or encountered specific patterns
                patterns = [pexpect.EOF, pexpect.TIMEOUT, r"[Pp]assword:"]
                if is_smbclient:
                    patterns.append(r"smb:\s*>")  # Detect smbclient prompt

                match_index = process.expect(patterns, timeout=60)

                if match_index == 0:  # EOF (process finished)
                    finished = True

                elif match_index == 1:  # TIMEOUT
                    self.console.print("[bold red]Command timed out after 1 minute.[/bold red]")
                    stderr_lines.append("Command timed out.")
                    process.terminate(force=True)
                    break

                elif match_index == 2:  # Password prompt detected
                    process.sendline("kali")
                    self.console.print("[bold yellow]Password entered automatically.[/bold yellow]")

                elif is_smbclient and match_index == 3:  # smbclient prompt detected
                    process.sendline("")  # Send Enter to bypass the smbclient prompt
                    self.console.print("[bold yellow]Entered smbclient session. Sent 'Enter' automatically.[/bold yellow]")

                # Capture any output before the next pattern match
                if process.before:
                    output_line = process.before.strip()
                    if output_line:
                        self.console.print(f"[bold green]{output_line}[/bold green]")
                        stdout_lines.append(output_line)

            # Ensure the process is closed
            process.close()

            # Handle cases where the process exits with an error code
            if process.exitstatus != 0:
                error_message = "".join(stderr_lines) if stderr_lines else "Command failed with unknown error."
                self.console.print(f"[bold red]Command failed with return code {process.exitstatus}.[/bold red]")
                self.console.print(f"[bold red]Error details: {error_message.strip()}[/bold red]")

                # Return error details for further handling
                return {"status": "error", "message": error_message.strip()}

            # Return the captured stdout as a single string
            return {"status": "success", "message": "\n".join(stdout_lines)}

        except FileNotFoundError:
            error_message = "Command not found. Ensure the command is valid and try again."
            self.console.print(f"[bold red]Error: {error_message}[/bold red]")
            return {"status": "error", "message": error_message}

        except Exception as e:
            error_message = f"Unexpected error executing command: {str(e)}"
            self.console.print(f"[bold red]{error_message}[/bold red]")
            return {"status": "error", "message": error_message}





    


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
        If GPT does not return a valid response, attempt to extract a command directly from the input.
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

            # If GPT provides a response, attempt to extract a command
            if extracted_command_response:
                matches = re.findall(r'```(?:bash)?\s*(.*?)\s*```', extracted_command_response, re.DOTALL)
                if matches:
                    command = matches[0].strip().split()
                    self.console.print(f"[bold green]Command extracted by GPT: {' '.join(command)}[/bold green]")
                    return command

                self.console.print("[bold yellow]GPT did not suggest a valid command. Falling back to regex extraction.[/bold yellow]")

            # Fallback: Use regex on the original response if GPT fails or returns None
            matches = re.findall(r'```(?:bash)?\s*(.*?)\s*```', response, re.DOTALL)
            if matches:
                # Extract the first match as a potential command
                potential_command = matches[0].strip().split()
                self.console.print(f"[bold green]Command extracted from input: {' '.join(potential_command)}[/bold green]")
                return potential_command

            # If no command is found, log a warning
            self.console.print("[bold yellow]No command could be extracted from GPT response or input.[/bold yellow]")
            return None

        except Exception as e:
            self.console.print(f"[bold red]Error extracting command with GPT: {str(e)}[/bold red]")
            return None



    def metasploit_script(self):
        """
        Generate and execute a Metasploit .rc script in a new terminal window.
        """
        try:
            # Prepare the prompt to include the full conversation history
            conversation_context = "".join(
                [f"{entry['role'].capitalize()}: {entry['content']}\n\n" for entry in self.history]
            )
            prompt = (
                "Based on the penetration testing context provided below, generate a Metasploit resource (.rc) script "
                "that automates the exploitation process. The script should be specific to the vulnerabilities identified, "
                "explicitly reference the target IP, and include clear comments for each step.\n\n"
                f"{conversation_context}\n\n"
                "The generated .rc script should:\n"
                "1. Set up the Metasploit framework environment.\n"
                "2. Use an appropriate exploit module.\n"
                "3. Set required payloads and options (e.g., RHOSTS, LHOST, LPORT).\n"
                "4. Include comments explaining each step.\n"
                "5. Save the results and maintain logs.\n"
                "Please enclose the script in triple backticks (` ``` `) for clarity."
            )

            # Send the prompt to GPT
            self.console.print("[bold blue]Requesting Metasploit script from GPT...[/bold blue]")
            response = self.send_to_gpt(prompt)

            if not response:
                self.console.print("[bold yellow]GPT did not return a response.[/bold yellow]")
                return None

            # Extract the .rc script from GPT's response
            matches = re.findall(r'```(?:bash|plaintext)?\s*(.*?)\s*```', response, re.DOTALL)
            if matches:
                metasploit_script = matches[0].strip()
                self.console.print(f"[bold green]Generated Metasploit Script:\n{metasploit_script}[/bold green]")

                # Save the script to a file
                script_path = os.path.join(self.log_dir, "metasploit_exploit.rc")
                with open(script_path, "w") as script_file:
                    script_file.write(metasploit_script)

                self.console.print(f"[bold green]Metasploit script saved to: {script_path}[/bold green]")

                # Execute the script in a new terminal window using pexpect
                self.execute_metasploit_script(script_path)

                return script_path
            else:
                self.console.print("[bold yellow]GPT did not generate a valid script.[/bold yellow]")
                return None

        except Exception as e:
            self.console.print(f"[bold red]Error generating Metasploit script: {str(e)}[/bold red]")
            return None


    def execute_metasploit_script(self, script_path):
        """
        Execute the Metasploit .rc script in a new terminal window.
        """
        try:
            self.console.print("[bold blue]Starting Metasploit with the generated script...[/bold blue]")

            # Prepare the command to run Metasploit with the script
            command = f"msfconsole -r {script_path}"

            # Open a new terminal window and run the command using pexpect
            child = pexpect.spawn(f"x-terminal-emulator -e {command}", timeout=3600)
            child.logfile = sys.stdout  # Redirect output to the current console for live updates

            # Wait for the process to complete or timeout
            child.expect(pexpect.EOF)
            self.console.print("[bold green]Metasploit execution completed.[/bold green]")

        except pexpect.TIMEOUT:
            self.console.print("[bold red]Metasploit execution timed out.[/bold red]")
        except Exception as e:
            self.console.print(f"[bold red]Error executing Metasploit script: {str(e)}[/bold red]")


    def check_and_run_metasploit(self, response):
        """
        Check if Metasploit is applicable based on the GPT response, and if so, generate and run a Metasploit script.
        """
        try:
            self.console.print("[bold blue]Checking if Metasploit is applicable...[/bold blue]")

            # Prepare a prompt to determine Metasploit applicability
            prompt = (
                "Based on the following context, determine if Metasploit can be used for exploitation.\n"
                "If Metasploit is applicable, generate a resource (.rc) script that automates the exploitation process "
                "and include all required settings (e.g., RHOSTS, LHOST, LPORT). Ensure to set:\n"
                f"- RHOSTS: {self.target_ip}\n"
                f"- LHOST: {self.my_ip}\n"
                "Choose a valid LPORT (e.g., 4444 or 5555) and include it in the script.\n\n"
                f"Context:\n{response}\n\n"
                "If Metasploit is applicable, enclose the script in triple backticks (` ``` `) for clarity."
            )

            # Ask GPT if Metasploit is applicable
            metasploit_response = self.send_to_gpt(prompt)

            if not metasploit_response:
                self.console.print("[bold yellow]GPT did not suggest using Metasploit.[/bold yellow]")
                return

            # Extract the Metasploit script from the GPT response
            matches = re.findall(r'```(?:bash|plaintext)?\s*(.*?)\s*```', metasploit_response, re.DOTALL)
            if matches:
                metasploit_script = matches[0].strip()
                self.console.print(f"[bold green]Generated Metasploit Script:\n{metasploit_script}[/bold green]")

                # Save the script to a file
                script_path = os.path.join(self.log_dir, "metasploit_exploit.rc")
                with open(script_path, "w") as script_file:
                    script_file.write(metasploit_script)

                self.console.print(f"[bold green]Metasploit script saved to: {script_path}[/bold green]")

                # Execute the Metasploit script
                self.execute_metasploit_script(script_path)
            else:
                self.console.print("[bold yellow]Metasploit is not applicable or GPT did not generate a valid script.[/bold yellow]")

        except Exception as e:
            self.console.print(f"[bold red]Error checking Metasploit applicability: {str(e)}[/bold red]")


    def execute_metasploit_script(self, script_path):
        """
        Execute the Metasploit .rc script directly within the application.
        """
        try:
            self.console.print("[bold blue]Starting Metasploit with the generated script...[/bold blue]")

            # Prepare the Metasploit command
            command = f"msfconsole -r {script_path}"

            # Use pexpect to execute the command
            child = pexpect.spawn(command, timeout=3600, encoding='utf-8')
            child.logfile_read = sys.stdout  # Redirect output to the console

            # Monitor the Metasploit execution
            child.expect(pexpect.EOF)
            self.console.print("[bold green]Metasploit execution completed.[/bold green]")

        except pexpect.TIMEOUT:
            self.console.print("[bold red]Metasploit execution timed out.[/bold red]")
        except Exception as e:
            self.console.print(f"[bold red]Error executing Metasploit script: {str(e)}[/bold red]")




    def start_conversation(self):
        """
        Start the main penetration testing workflow with enhanced error handling.
        Includes Metasploit integration for exploitation when applicable.
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

        while retry_count <= max_retries:
            try:
                # Extract a command using GPT
                command = self.extract_command_with_gpt(response)

                if not command:
                    retry_count += 1
                    self.console.print(f"[bold yellow]Retrying... ({retry_count}/{max_retries})[/bold yellow]")
                    
                    if retry_count > max_retries:
                        self.console.print("[bold yellow]Max retries reached. Exiting conversation.[/bold yellow]")
                        break
                    
                    response = self.send_to_gpt(
                        "GPT did not suggest a valid command. Please analyze the previous task and suggest the next steps."
                    )
                    continue

                # Reset retry count if a valid command is found
                retry_count = 0

                # Validate the command
                is_valid, validation_message = self.validate_command(command)
                if not is_valid:
                    self.console.print(f"[bold red]Command validation failed: {validation_message}[/bold red]")
                    response = self.send_to_gpt(f"Command validation failed: {validation_message}. Suggest next steps.")
                    continue

                # Execute the command inline
                self.console.print(f"[bold blue]Executing command: {' '.join(command)}[/bold blue]")
                command_output = self.execute_command(command)

                # if command_output is None:  # Command failed or returned no output
                #     self.console.print("[bold red]Command execution failed or returned no output.[/bold red]")
                #     response = self.send_to_gpt(
                #         f"The command `{command}` failed or produced no output.\n"
                #         f"Error details (if any):\n\n```plaintext\n{command_output or 'No details available.'}\n```\n"
                #         f"Please suggest an alternative command or next steps."
                #     )
                #     continue

                # # Provide the command output to GPT for analysis
                # self.console.print(f"[bold green]Command Output:\n{command_output}[/bold green]")
                # response = self.send_to_gpt(
                #     f"The following is the output of the command `{command}`:\n\n```plaintext\n{command_output}\n```\n"
                #     f"Analyze this output and suggest the next steps in the penetration testing process."
                # )

                if command_output is None:  # Command failed or returned no output
                    self.console.print("[bold red]Command execution failed or returned no output.[/bold red]")

                    # Include full chat history when requesting suggestions
                    conversation_context = "\n".join(
                        f"User: {entry['user']}\nGPT: {entry['gpt']}" for entry in self.history
                    )
                    failure_prompt = (
                        f"{conversation_context}\n\n"
                        f"User: The command `{command}` failed or produced no output.\n"
                        f"Please suggest an alternative command or next steps.\nGPT:"
                    )

                    response = self.send_to_gpt(failure_prompt)
                    if response:
                        self.history.append({"user": failure_prompt, "gpt": response})
                    continue

                # Provide the command output to GPT for analysis, with full history
                self.console.print(f"[bold green]Command Output:\n{command_output}[/bold green]")

                conversation_context = "\n".join(
                    f"User: {entry['user']}\nGPT: {entry['gpt']}" for entry in self.history
                )
                analysis_prompt = (
                    f"{conversation_context}\n\n"
                    f"User: The following is the output of the command `{command}`:\n\n"
                    f"```plaintext\n{command_output}\n```\n"
                    f"Analyze this output and suggest the next steps in the penetration testing process.\nGPT:"
                )

                response = self.send_to_gpt(analysis_prompt)
                if response:
                    self.history.append({"user": analysis_prompt, "gpt": response})


                # Check if Metasploit is applicable based on the response
                self.check_and_run_metasploit(response)

            except KeyboardInterrupt:
                self.console.print("[bold red]Interrupted by user. Exiting conversation.[/bold red]")
                break
            except Exception as e:
                self.console.print(f"[bold red]Unexpected error: {str(e)}[/bold red]")
                response = self.send_to_gpt(
                    f"An unexpected error occurred during the penetration testing process:\n\n```plaintext\n{str(e)}\n```\n"
                    f"Please analyze this and suggest a way to continue."
                )
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
