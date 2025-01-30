export async function POST(req) {
    try {
      const { target_ip } = await req.json();
  
      if (!target_ip) {
        return new Response(JSON.stringify({ error: "Missing target_ip" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
  
      const response = await fetch("http://localhost:5678/webhook-test/trigger_scan", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ target_ip }),
      });
  
      if (!response.ok) {
        return new Response(
          JSON.stringify({ error: "Failed to trigger scan" }),
          { status: 500, headers: { "Content-Type": "application/json" } }
        );
      }
  
      return new Response(
        JSON.stringify({ message: "Scan triggered successfully" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    } catch (error) {
      return new Response(
        JSON.stringify({ error: "Server error", details: error.message }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }
  }
  