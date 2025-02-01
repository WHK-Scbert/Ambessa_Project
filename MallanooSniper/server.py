from flask import Flask, request
from flask_socketio import SocketIO
import subprocess
import threading
import queue
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Queue to store Metasploit output
output_queue = queue.Queue()

# Start Metasploit process
msf_process = subprocess.Popen(['msfconsole', '-q'],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True,
                               bufsize=1)

def read_output():
    """Reads Metasploit output and emits it through SocketIO."""
    for line in iter(msf_process.stdout.readline, ''):
        socketio.emit("output", line)

def generate_output():
    """Yields Metasploit output to be sent as a response stream."""
    while True:
        try:
            line = output_queue.get(timeout=1)
            socketio.emit("output", line)
        except queue.Empty:
            continue

# Start reading Metasploit output in a separate thread
threading.Thread(target=read_output, daemon=True).start()

@socketio.on("command")
def send_command(data):
    """Receives a command from the frontend and sends it to Metasploit."""
    if isinstance(data, str):
        command = data
    elif isinstance(data, dict):
        command = data.get("command", "")
    else:
        socketio.emit("error", {"status": "error", "message": "Invalid data format"})
        return

    if command:
        msf_process.stdin.write(command + '\n')
        msf_process.stdin.flush()
        socketio.emit("confirmation", {"status": "sent", "command": command})
    else:
        socketio.emit("error", {"status": "error", "message": "No command provided"})

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles uploading an .rc file and executes it in Metasploit."""
    if 'file' not in request.files:
        return {"status": "error", "message": "No file part"}, 400
    
    file = request.files['file']
    if file.filename == '':
        return {"status": "error", "message": "No selected file"}, 400
    
    file_path = os.path.join("/tmp", file.filename)
    file.save(file_path)
    
    msf_process.stdin.write(f"resource {file_path}\n")
    msf_process.stdin.flush()
    
    return {"status": "success", "message": "File uploaded and executed"}

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
