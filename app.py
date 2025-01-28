from flask import Flask, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import subprocess
import threading

import io
from contextlib import redirect_stdout

# === MallanooSploit / PentestGPT imports ===
from prompts.prompt_class import PentestGPTPrompt
from mallanoo_sploit import MallanooSploit

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Session or state data if needed
sessions = {
    "initialized": False,
}

def run_shell_command(command, command_id):
    """
    Executes a shell command in a subprocess and emits each line of stdout to the client.
    """
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in iter(process.stdout.readline, b""):
            socketio.emit(f"output_{command_id}", {"data": line.decode("utf-8")})
    except Exception as e:
        socketio.emit(f"output_{command_id}", {"data": f"Error running command: {str(e)}"})


def run_mallanoo_sploit(target_ip, command_id, description=""):
    """
    Runs MallanooSploit (PentestGPT) logic in Python, captures stdout, and emits each line to the client.
    """
    try:
        # Use StringIO to capture all prints from MallanooSploit
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            # Print a quick header so we know it started
            print(f"=== Starting MallanooSploit on {target_ip} ===")

            if not sessions["initialized"]:
                sessions["initialized"] = True

            # Create a MallanooSploit instance
            pentest_handler = MallanooSploit(
                target_ip=target_ip,
                target_description=description,
            )
            pentest_handler.start_conversation()  # This may produce print() output

            print("=== MallanooSploit Finished ===")

        # Now read what was printed line by line and emit
        lines = buffer.getvalue().splitlines()
        for line in lines:
            socketio.emit(f"output_{command_id}", {"data": line})
            socketio.sleep(0.05)  # small delay so the client sees streaming effect
    except Exception as e:
        socketio.emit(f"output_{command_id}", {"data": f"Error running MallanooSploit: {str(e)}"})


@app.route("/api/scan", methods=["POST"])
def scan():
    """
    Accepts JSON with {"ip": "..."} and starts two parallel threads:
      1) A shell command (ping)
      2) MallanooSploit logic
    Both outputs are streamed to the client via Socket.IO
    """
    data = request.json or {}
    ip = data.get("ip")
    if not ip:
        return {"error": "IP address is required"}, 400

    # Example shell commands (you can modify them as desired)
    # We'll just do ping here. The second is replaced by MallanooSploit.
    command1 = f"ping {ip} -c 4"

    # Start both commands in parallel
    #  - We'll re-use your existing socketio channels: output_1 and output_2
    threading.Thread(target=run_shell_command, args=(command1, 1)).start()
    threading.Thread(target=run_mallanoo_sploit, args=(ip, 2, "Demo target")).start()

    return {"message": "Scan started"}


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5500)
