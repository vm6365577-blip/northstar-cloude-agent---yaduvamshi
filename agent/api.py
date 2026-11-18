"""
NorthStar Retail - Web API & Development Server
Lightweight FastAPI server replacing 'adk web' for Amazon Bedrock.
Provides both a REST API (/chat) and an interactive web chat UI.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from agent.agent import root_agent

app = FastAPI(
    title="NorthStar Retail AI Assistant (AWS Bedrock)",
    description="Conversational Business Intelligence and Policy Assistant powered by Amazon Bedrock and S3 Lakehouse.",
    version="2.0.0",
)


class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    query: str
    response: str


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "agent": "NorthStar Retail Bedrock Agent",
        "cloud_provider": "AWS",
        "model": root_agent.model_id,
        "region": root_agent.region_name,
    }


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    answer = root_agent.ask(request.query)
    return ChatResponse(query=request.query, response=answer)


@app.get("/", response_class=HTMLResponse)
def web_ui():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NorthStar Retail - AWS Bedrock Assistant</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; display: flex; justify-content: center; }
        .container { max-width: 800px; width: 100%; display: flex; flex-direction: column; height: 90vh; }
        .header { padding: 16px; background: #1e293b; border-radius: 12px 12px 0 0; border-bottom: 2px solid #38bdf8; display: flex; align-items: center; justify-content: space-between; }
        .header h1 { font-size: 1.25rem; margin: 0; color: #38bdf8; }
        .badge { background: #0284c7; padding: 4px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: bold; }
        .chat-box { flex: 1; background: #1e293b; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
        .message { padding: 12px 16px; border-radius: 10px; max-width: 80%; line-height: 1.5; white-space: pre-wrap; font-size: 0.95rem; }
        .user { align-self: flex-end; background: #2563eb; color: #ffffff; }
        .agent { align-self: flex-start; background: #334155; color: #e2e8f0; border: 1px solid #475569; }
        .input-bar { display: flex; gap: 10px; padding: 16px; background: #1e293b; border-radius: 0 0 12px 12px; border-top: 1px solid #334155; }
        input[type="text"] { flex: 1; padding: 12px 16px; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: white; font-size: 1rem; }
        input[type="text"]:focus { outline: none; border-color: #38bdf8; }
        button { padding: 12px 24px; background: #0284c7; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
        button:hover { background: #0369a1; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>NorthStar Retail AI Assistant</h1>
                <small style="color: #94a3b8;">Powered by Amazon Bedrock & Athena Gold Lakehouse</small>
            </div>
            <span class="badge">AWS Production Ready</span>
        </div>
        <div class="chat-box" id="chat">
            <div class="message agent">Welcome to NorthStar Retail. How can I help you with sales metrics or store policies today?</div>
        </div>
        <div class="input-bar">
            <input type="text" id="userInput" placeholder="Ask: 'What are the top 5 products?' or 'What is the return policy?'" onkeydown="if(event.key==='Enter') sendMessage()" />
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>
    <script>
        async function sendMessage() {
            const input = document.getElementById("userInput");
            const text = input.value.trim();
            if (!text) return;
            appendMessage(text, "user");
            input.value = "";

            const chat = document.getElementById("chat");
            const loadingDiv = document.createElement("div");
            loadingDiv.className = "message agent";
            loadingDiv.innerText = "Analyzing lakehouse data...";
            chat.appendChild(loadingDiv);
            chat.scrollTop = chat.scrollHeight;

            try {
                const res = await fetch("/chat", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({query: text})
                });
                const data = await res.json();
                chat.removeChild(loadingDiv);
                appendMessage(data.response, "agent");
            } catch (err) {
                chat.removeChild(loadingDiv);
                appendMessage("Error querying assistant: " + err, "agent");
            }
        }
        function appendMessage(text, sender) {
            const chat = document.getElementById("chat");
            const msg = document.createElement("div");
            msg.className = "message " + sender;
            msg.innerText = text;
            chat.appendChild(msg);
            chat.scrollTop = chat.scrollHeight;
        }
    </script>
</body>
</html>
    """


def start_server(host: str = "127.0.0.1", port: int = 8000):
    print(f"\nStarting NorthStar Retail Assistant on http://{host}:{port}")
    uvicorn.run("agent.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    start_server()
