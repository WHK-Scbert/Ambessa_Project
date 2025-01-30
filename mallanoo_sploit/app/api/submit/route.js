let storedData = null; // Temporary storage (Use a database for persistence)

export async function POST(req) {
    try {
        const body = await req.json();
        storedData = body; // Store the latest data
        console.log("Received data:", body);

        return new Response(JSON.stringify({ message: "Data received", received: body }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
        });
    } catch (error) {
        return new Response(JSON.stringify({ error: "Invalid request" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
        });
    }
}

export async function GET() {
    return new Response(JSON.stringify(storedData || { message: "No data received yet" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
    });
}
