Here are the precise steps tailored to your setup:

Step 1 — Download the installer:
Go to ollama.com/download and click Download for Windows.

Step 2 — Run the installer:
Open the downloaded OllamaSetup.exe and follow the prompts. It installs Ollama and starts it as a background service automatically.

Step 3 — Open a new PowerShell terminal (important — the old one won't have the updated PATH), then verify:


ollama --version


Running Ollama Models Locally on Windows
Step 1 — Fix PATH (one-time)
Open PowerShell and run:


[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$env:LOCALAPPDATA\Programs\Ollama", "User")
Restart PowerShell. Now ollama will work without the full path.

Step 2 — Verify Ollama is running

curl http://localhost:11434
Expected output: Ollama is running

If not running, launch the desktop app from Start Menu → Ollama.

Step 3 — Pull models
For your RAG notebook you need two models:


ollama pull nomic-embed-text   # embeddings (~274 MB)
ollama pull llama3.2           # chat model (~2 GB)
Step 4 — Verify models are downloaded

ollama list
You should see both nomic-embed-text and llama3.2.

Step 5 — Test the chat model interactively (optional)

ollama run llama3.2
Type a message and press Enter. Type /bye to exit.


Quick reference
Command	Purpose
ollama list	See downloaded models
ollama pull <model>	Download a model
ollama run <model>	Chat interactively
ollama rm <model>	Delete a model
ollama ps	See currently loaded models
Ollama starts automatically with Windows via the desktop app, so you don't need to do anything special on reboot — just open your notebook and run.

