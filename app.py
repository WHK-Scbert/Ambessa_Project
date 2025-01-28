from flask import Flask, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import io
from contextlib import redirect_stdout
import threading

# Your custom imports
import openai  # if needed
import os      # if needed
from prompts.prompt_class import PentestGPTPrompt
from mallanoo_sploit import MallanooSploit

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Load prompts, if needed
prompts = PentestGPTPrompt()

# Keep track of some session details if you want
sessions = {
    "initialized": False,
    "target_ip": None,
    "reasoning_session": None,
    "generation_session": None,
}

def run_pentest(target_ip, target_description):
    """
    Runs a penetration test and prints output. The printed output will be
    captured and streamed to the client via Socket.IO.
    """
    print(f"Running pentest on IP: {target_ip}")
    print(f"Description: {target_description}")

    if not target_ip:
        print("No target IP provided.")
        return  # We'll just print an error and stop.

    # Initialize only once (optional logic, if you prefer)
    if not sessions["initialized"]:
        sessions["initialized"] = True
        pentest_handler = MallanooSploit(
            target_ip=target_ip,
            target_description=target_description,
        )
        # start_conversation() presumably prints or logs info
        pentest_handler.start_conversation()

@app.route("/api/pentest", methods=["POST"])
def pentest_route():
    """
    API endpoint to start a pentest and stream its output in real time
    via Socket.IO events called 'pentest_output'.
    """
    data = request.json or {}
    ip = data.get("ip")
    desc = data.get("description", "No description provided.")

    if not ip:
        return {"error": "IP address is required"}, 400

    # We'll run the pentest in a background task so we don't block the Flask worker
    def background_pentest():
        # Use StringIO to capture printed output from run_pentest()
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            run_pentest(ip, desc)
        # Once run_pentest() finishes, buffer has everything printed
        lines = buffer.getvalue().splitlines()

        # Stream each line to the frontend
        for line in lines:
            socketio.emit("pentest_output", {"data": line})
            socketio.sleep(0.05)  # short sleep so client sees real-time updates

    # Kick off the background task
    socketio.start_background_task(background_pentest)

    return {"message": "Pentest started"}

if __name__ == "__main__":
    # Run Flask-SocketIO
    socketio.run(app, host="0.0.0.0", port=5000)
