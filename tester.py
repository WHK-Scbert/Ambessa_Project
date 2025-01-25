from flask import Flask, request, jsonify
import openai
import os
from prompts.prompt_class import PentestGPTPrompt
from ambessa2 import SimplifiedPentestGPT


# Initialize OpenAI API key (set this as an environment variable)

# Load prompts
prompts = PentestGPTPrompt()

# State to track session details
sessions = {
    "initialized": False,
    "target_ip": None,
    "reasoning_session": None,
    "generation_session": None,
}


def run_pentest(target_ip, target_description):
    """
    Runs a penetration test and returns the results as JSON.
    """
    print(f"Target IP: {target_ip}")
    print(f"Description: {target_description}")

    if not target_ip:
        return {"error": "No target IP provided."}, 400

    # Initialize the conversation
    if not sessions["initialized"]:
        # Initialize the conversation with the user input
        sessions["initialized"] = True
        pentest_handler = SimplifiedPentestGPT(
            target_ip=target_ip,
            target_description=target_description,
        )

        pentest_handler.start_conversation()

    return "message"

def chat():
    """
    Handles requests from the Next.js app and returns results.
    """

    # Parse user input from the request
    target_ip = '192.168.74.25'
    target_description = 'Test target'

    # Run the penetration test and get results
    run_pentest(target_ip=target_ip, target_description=target_description)



if __name__ == "__main__":
    chat()
