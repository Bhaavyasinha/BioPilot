# BioPilot web app — run it & put it online

This is a real, working web app. The safety-checker, parser, and benchmark you
see in the browser are powered by BioPilot's actual code (in the `biopilot/`
folder here). The genomics *execution* result is pre-computed for the public
demo; everything else runs live.

## Run it on your own computer first

1. Open a terminal **in this `webapp` folder**.
2. Install the requirements:
   ```
   pip install -r requirements.txt
   ```
3. Start the server:
   ```
   python app.py
   ```
4. Open your browser to **http://localhost:5000** — that's your site, running live.
   Press Ctrl+C in the terminal to stop it.

## Put it online for free (so anyone can visit)

A "server" is just an always-on computer in the cloud. These hosts give you one
free:

### Option A — Render (simple, recommended)
1. Push this `webapp` folder to a GitHub repo (we can do this together).
2. Go to https://render.com → sign up (free) → **New → Web Service**.
3. Connect your GitHub repo.
4. Settings:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
5. Click **Create Web Service**. In a few minutes you get a public link like
   `https://biopilot.onrender.com`.

### Option B — Hugging Face Spaces
1. Go to https://huggingface.co/spaces → **Create new Space** → SDK: **Docker**
   (or use the Gradio template and adapt).
2. Upload these files. It builds and gives you a public link.

## Files
- `app.py` — the Flask server (the API).
- `templates/index.html` — the website you see.
- `biopilot/` — your actual project code that powers the demo.
- `requirements.txt`, `Procfile` — tell the host how to run it.
