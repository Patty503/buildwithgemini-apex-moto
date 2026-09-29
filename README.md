# ApexMoto • High-Performance Motorcycle Route Concierge

ApexMoto is an agentic motorcycle concierge and group-ride assistant built on the Google Agent Development Kit (ADK) and Gemini. It helps riders discover high-twistiness roads, monitor real-time crew positions and riding telemetry, check mountain pavement weather conditions, compute dynamic lean angle physics in a code execution sandbox, and generate cinematic visual posters and video clips of routes and bikes.

ApexMoto features a responsive dialogue web frontend talking directly to the agent over the A2A protocol, natively rendering Google Agent-to-UI (A2UI v0.8) cards.

---

## What ApexMoto Implements

ApexMoto implements and wires the following Google Cloud and Agent Platform capabilities:

1. **Agent Model**: Powered by `gemini-3.6-flash` through ADK.
2. **Cross-Session Long-Term Memory (Vertex AI Memory Bank)**:
   - Uses `PreloadMemoryTool` to load past rider context at session start.
   - Saves preferences, riding styles (e.g. canyon carver vs. cruiser), favorite bikes, and past route history via an `after_agent_callback` to an Agent Engine managed Memory Bank.
3. **Firestore Database**:
   - `search_routes`: Queries curated routes filtered by twistiness ratings (1–10), geographic region, and recommended bike types.
   - `get_route_details`: Fetches route metadata, surface conditions, elevation gain, and landmarks.
   - `add_custom_route`: Persists user-submitted routes with slugified IDs and elevation profiles.
   - `get_crew_status`: Retrieves live telemetry for convoy riders (coordinates, current road, speed in mph, battery level, heading).
   - `record_user_social_action`: Logs rider likes, comments, and route bookmarks.
4. **Agent Engine Sandbox Code Executor**:
   - Executes Python calculations in a remote sandbox environment (e.g., lean angle physics: $\theta = \arctan(v^2 / (r \cdot g))$, fuel consumption estimates, and elevation delta analysis).
5. **Weather & Road Hazards**:
   - `check_road_weather`: Calls Open-Meteo API for real-time temperature, wind speed, precipitation, and motorcycle-specific tire grip / lean caution advice.
6. **AI Media Generation & Public Cloud Storage**:
   - `generate_route_image`: Generates cinematic motorcycle and scenic photography using `gemini-3.1-flash-lite-image` in `location="global"`.
   - `generate_route_video`: Generates short cinematic video clips using Google's Omni model (`gemini-omni-flash-preview`) in `location="global"` via the Interactions streaming API.
   - Both media tools save artifacts directly to the ADK Playground's Artifacts panel via `tool_context.save_artifact` and upload the bytes to a public Cloud Storage bucket.
7. **Rich Display with A2UI (Agent-to-UI v0.8)**:
   - Generates structured, flat cards (`Card`, `Column`, `Row`, `Text`, `Image`) rendered natively in both ADK Web and the custom web frontend.

---

## Project Structure

```
├── README.md                      # Project documentation
├── project_brief.md               # Architecture design & brief
├── apex-moto/                     # ADK Agent application
│   ├── app/
│   │   ├── agent.py               # Core ADK agent, tools, schema manager, callbacks
│   │   ├── a2ui_utils.py          # A2UI callback formatting & card structuring
│   │   └── fast_api_app.py        # ADK FastAPI wrapper
│   ├── pyproject.toml             # Python dependencies
│   └── agents-cli-manifest.yaml   # Agent Engine deployment manifest
└── frontend/                      # Web frontend & A2A proxy
    ├── main.py                    # FastAPI proxy talking A2A protocol to agent
    ├── static/
    │   └── index.html             # Responsive dialogue UI & A2UI renderer
    └── Dockerfile                 # Container build for deployment
```

---

## Running Locally

### 1. Run the Agent Locally with ADK Web

Ensure Google Cloud credentials and environment variables are active:

```bash
cd apex-moto
uv run adk web . --port 8080 --reload_agents
```

Open your browser to the local ADK Web interface to inspect memory, tools, and A2UI card outputs.

### 2. Run the Custom Dialogue Frontend

In a separate terminal:

```bash
cd frontend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set the deployed Agent Engine resource name or local endpoint
export AGENT_ENGINE_RESOURCE_NAME="<YOUR_AGENT_ENGINE_RESOURCE_NAME>"
export AGENT_DIRECTORY="app"
export PORT=8080

python main.py
```

---

## Cloud Deployment

- **Agent Engine**: Deployed to Vertex AI Agent Platform with `agents-cli deploy`.
- **Frontend**: Containerized via Docker and deployed to Google Cloud Run with `roles/aiplatform.user` granted to call the Agent Runtime.
