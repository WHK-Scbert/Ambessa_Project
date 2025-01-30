import { NextResponse } from "next/server";
import { WebSocketServer } from "ws";

let wss; // WebSocket server instance

export async function GET() {
  if (!wss) {
    wss = new WebSocketServer({ port: 5501 });

    wss.on("connection", (ws) => {
      console.log("New WebSocket client connected.");

      ws.on("message", (message) => {
        console.log(`Received message: ${message}`);
      });

      ws.on("close", () => {
        console.log("WebSocket client disconnected.");
      });
    });

    console.log("WebSocket server initialized.");
  }

  return NextResponse.json({ message: "WebSocket API is running" });
}
