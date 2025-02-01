"use client";
import { useEffect, useState } from 'react';
import io from 'socket.io-client';
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

const socket = io("http://localhost:5000");

export default function MetasploitDashboard() {
    const [output, setOutput] = useState("");
    const [command, setCommand] = useState("");
    const [file, setFile] = useState(null);

    useEffect(() => {
        socket.on("output", (data) => {
            setOutput(prev => prev + data + "\n");
        });
        return () => socket.off("output");
    }, []);

    const sendCommand = () => {
        socket.emit("command", command.trim());
        setCommand("");
    };

    const uploadFile = async () => {
        if (!file) return;
        const formData = new FormData();
        formData.append("file", file);
        
        await fetch("http://localhost:5000/upload", {
            method: "POST",
            body: formData,
        });
    };

    return (
        <div className="min-h-screen bg-gray-950 text-green-400 p-6 font-mono flex flex-col items-center gap-6">
            <h1 className="text-3xl font-extrabold mb-4 text-blue-400 border-b-2 border-blue-500 pb-2 uppercase tracking-wide">
                MallnooSploit - <span className="text-red-500">SNIPER SERVICE</span>
            </h1>
            <Card className="w-full max-w-3xl bg-gray-900 p-4 rounded-lg shadow-lg border border-blue-500 h-[500px] flex flex-col">
                <CardContent className="flex-grow overflow-y-auto">
                    <pre className="h-full bg-black p-4 rounded-md border border-green-500 text-green-300 text-sm">
                        {output || "Waiting for Metasploit output..."}
                    </pre>
                </CardContent>
            </Card>
            <div className="flex space-x-4 w-full max-w-3xl">
                <Input
                    className="flex-grow bg-gray-800 text-white border border-blue-500 p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400"
                    placeholder="Enter command"
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                />
                <Button onClick={sendCommand} className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-500 transition">Send</Button>
            </div>
            <div className="flex space-x-4 w-full max-w-3xl mt-4">
                <input
                    type="file"
                    className="text-white"
                    onChange={(e) => setFile(e.target.files[0])}
                />
                <Button onClick={uploadFile} className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-500 transition">Upload .rc File</Button>
            </div>
        </div>
    );
}
