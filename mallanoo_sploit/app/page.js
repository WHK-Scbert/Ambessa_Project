"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";

export default function CyberApp() {
  const [ipAddress, setIpAddress] = useState("");
  const [output, setOutput] = useState("");
  const [status, setStatus] = useState("Idle");

  useEffect(() => {
    const socket = new WebSocket("ws://localhost:5501");

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setOutput((prev) => prev + `\n${data.output}`);
    };

    return () => {
      socket.close();
    };
  }, []);

  const handleFire = async () => {
    setStatus("Running");
    setOutput("");
  
    const response = await fetch("/api/send-scan", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ target_ip: ipAddress }),
    });
  
    if (response.ok) {
      setStatus("Processing");
    } else {
      setStatus("Error");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-800 text-white flex flex-col font-mono">
      <header className="p-4 flex justify-between items-center border-b border-gray-700 shadow-lg">
        <h1 className="text-2xl font-extrabold tracking-wide text-blue-500">
          CyberOps Interface
        </h1>
        <button className="px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-500 focus:ring-2 focus:ring-blue-400">
          SE
        </button>
      </header>

      <main className="flex-grow flex flex-col items-center justify-center relative p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8 }}
          className="absolute top-0 text-center text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-green-400 via-blue-500 to-purple-600 drop-shadow-lg"
        >
          MallanooSploit
        </motion.div>

        <div className="w-full max-w-7xl p-6 bg-gray-800 rounded-2xl shadow-lg">
          <h2 className="text-xl font-bold mb-4">Enter Target IP Address</h2>
          <div className="flex gap-4 mb-6">
            <input
              type="text"
              value={ipAddress}
              onChange={(e) => setIpAddress(e.target.value)}
              placeholder="e.g., 192.168.0.1"
              className="flex-grow px-4 py-2 rounded-lg bg-gray-700 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleFire}
              className="px-6 py-2 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-500 focus:ring-2 focus:ring-green-400"
            >
              Fire
            </button>
          </div>

          {/* Wider Output Grid */}
          <div className="grid grid-cols-1 gap-6">
            <pre className="bg-black text-green-400 p-6 rounded-lg h-80 overflow-auto border border-gray-600">
              {output || "Awaiting output..."}
            </pre>
          </div>
        </div>
      </main>

      <footer className="p-2 bg-gray-800 border-t border-gray-700">
        <motion.div
          initial={{ width: "0%" }}
          animate={{ width: status === "Processing" ? "100%" : "0%" }}
          className="h-2 bg-blue-500"
        />
        <p className="text-center text-gray-400 mt-2">Status: {status}</p>
      </footer>
    </div>
  );
}
