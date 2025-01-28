"use client";

import { useState } from "react";
import { motion } from "framer-motion";

export default function CyberApp() {
  const [ipAddress, setIpAddress] = useState("");
  const [output, setOutput] = useState("");
  const [status, setStatus] = useState("Idle");

  // const handleFire = async () => {
  //   setStatus("Running");
  //   setOutput("");

  //   // const eventSource = new EventSource(`/api/scan?ip=${ipAddress}`);
  //   // const eventSource = new EventSource(`http://192.168.1.46:5000/api/scan?ip=${ipAddress}`);
  //   const eventSource = new EventSource(`http://192.168.1.46:5000/api/scan?ip='192.168.251.190'`);


  //   eventSource.onmessage = (event) => {
  //     setOutput((prev) => prev + event.data + "\n");
  //   };

  //   eventSource.onerror = () => {
  //     setStatus("Error");
  //     eventSource.close();
  //   };

  //   eventSource.onopen = () => setStatus("Processing");

  //   eventSource.onclose = () => setStatus("Completed");
  // };

  const handleFire = async () => {
    console.log("Fire button clicked"); // Log to the console when the button is clicked
    setStatus("Running");
    setOutput("Initializing scan...\n"); // Add an initial message to the output
  
    const eventSource = new EventSource(`http://192.168.172.149:5000/api/scan?ip=${ipAddress}`);
  
    eventSource.onmessage = (event) => {
      console.log("Received data:", event.data); // Log received data
      setOutput((prev) => prev + event.data + "\n");
    };
  
    eventSource.onerror = () => {
      console.error("EventSource failed"); // Log any errors
      setStatus("Error");
      setOutput((prev) => prev + "Error: Connection failed.\n"); // Add an error message to the output
      eventSource.close();
    };
  
    eventSource.onopen = () => {
      console.log("EventSource connection opened"); // Log when the connection is opened
      setStatus("Processing");
    };
  
    eventSource.onclose = () => {
      console.log("EventSource connection closed"); // Log when the connection is closed
      setStatus("Completed");
    };
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
        {/* MallanooSploit Title */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8 }}
          className="absolute top-0 text-center text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-green-400 via-blue-500 to-purple-600 drop-shadow-lg"
        >
          MallanooSploit
        </motion.div>

        {/* IP Input and Output Box */}
        <div className="w-full max-w-3xl p-6 bg-gray-800 rounded-2xl shadow-lg">
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
          <pre className="bg-black text-green-400 p-4 rounded-lg h-64 overflow-auto border border-gray-600">
            {output || "Awaiting output..."}
          </pre>
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
