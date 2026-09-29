# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import re
from typing import Any, Dict, List, Optional
from google.cloud import firestore, storage
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.memory.base_memory_service import MemoryEntry
from google.adk.models import Gemini

from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import Client, types
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback





MODEL = "gemini-3.6-flash"

# Hardcoded project ID string (avoids project number mismatch on Agent Platform)
FIRESTORE_PROJECT = "qwiklabs-gcp-03-0447589ffaaa"

_db: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=FIRESTORE_PROJECT)
    return _db


def search_routes(
    min_twistiness: Optional[int] = None,
    region: Optional[str] = None,
    bike_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search motorcycle routes from Firestore by minimum twistiness rating, region, or bike type.

    Args:
        min_twistiness: Minimum twistiness rating from 1 to 10 (e.g. 8 or 9 for very twisty).
        region: Geographic region keyword (e.g., 'California', 'Tennessee', 'Malibu').
        bike_type: Type of bike (e.g., 'Sport', 'Adventure', 'Cruiser').

    Returns:
        A list of matching motorcycle route records.
    """
    db = get_firestore_client()
    docs = db.collection("routes").stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        if min_twistiness and data.get("twistiness_rating", 0) < min_twistiness:
            continue
        if region and region.lower() not in data.get("region", "").lower() and region.lower() not in data.get("name", "").lower():
            continue
        if bike_type and bike_type.lower() not in data.get("recommended_bike_type", "").lower():
            continue
        results.append(data)

    return results


def get_route_details(route_id: str) -> Dict[str, Any]:
    """Retrieve full details of a specific motorcycle route by ID or slug.

    Args:
        route_id: The identifier of the route (e.g., 'skyline-boulevard-ca35', 'tail-of-the-dragon-us129').

    Returns:
        The route details dictionary, or an error message if not found.
    """
    db = get_firestore_client()
    doc_ref = db.collection("routes").document(route_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {"error": f"Route '{route_id}' not found."}


def add_custom_route(
    name: str,
    region: str,
    distance_miles: float,
    twistiness_rating: int,
    surface_condition: str,
    highlight: str,
    recommended_bike_type: str = "Sport / Naked / Touring",
    elevation_gain_ft: int = 1500,
    scenic_rating: int = 8,
) -> Dict[str, Any]:
    """Add a new motorcycle route to the Firestore database.

    Args:
        name: Name of the route (e.g., 'Pacific Coast Highway Big Sur').
        region: Region or state where the road is located.
        distance_miles: Total length in miles.
        twistiness_rating: Curve density on a scale from 1 (straight highway) to 10 (intense hairpins/tail of the dragon).
        surface_condition: Description of the pavement/tarmac.
        highlight: What makes this route special (scenery, landmarks, curves).
        recommended_bike_type: Suggested bike style.
        elevation_gain_ft: Approximate elevation change in feet.
        scenic_rating: Scenic rating from 1 to 10.

    Returns:
        Confirmation dictionary with the created route ID and status.
    """
    db = get_firestore_client()
    route_id = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")

    route_data = {
        "id": route_id,
        "name": name,
        "region": region,
        "distance_miles": distance_miles,
        "twistiness_rating": twistiness_rating,
        "surface_condition": surface_condition,
        "elevation_gain_ft": elevation_gain_ft,
        "highlight": highlight,
        "recommended_bike_type": recommended_bike_type,
        "scenic_rating": scenic_rating,
    }

    db.collection("routes").document(route_id).set(route_data)
    return {"status": "success", "message": f"Route '{name}' successfully saved!", "route_id": route_id}


def get_crew_status(rider_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get the live status and riding location of crew members or a specific friend.

    Args:
        rider_name: Optional name of the rider (e.g. 'Alex', 'Marcus', 'Elena') to filter by.

    Returns:
        List of crew members with their current road, riding status, speed, battery, and heading.
    """
    db = get_firestore_client()
    docs = db.collection("crew_members").stream()

    crew = []
    for doc in docs:
        data = doc.to_dict()
        if rider_name and rider_name.lower() not in data.get("name", "").lower():
            continue
        crew.append(data)
    return crew


def check_road_weather(location_or_city: str) -> Dict[str, Any]:
    """Check current real-world weather, temperature, and wind speed for a riding location or city using the Open-Meteo public API.

    Args:
        location_or_city: City or area name (e.g., 'Malibu', 'San Francisco', 'Robbinsville', 'Red Lodge', 'Palo Alto').

    Returns:
        Current weather data including temperature (°F), windspeed (mph), weather condition, and motorcycle riding safety advice.
    """
    import requests

    try:
        geo_resp = requests.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={location_or_city}&count=1",
            timeout=5,
        )
        geo_data = geo_resp.json()
        results = geo_data.get("results")
        if not results:
            return {"error": f"Could not find coordinates for location: {location_or_city}"}

        first_match = results[0]
        lat = first_match["latitude"]
        lon = first_match["longitude"]
        place_name = f"{first_match.get('name')}, {first_match.get('admin1', '')}"

        weather_resp = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&temperature_unit=fahrenheit&windspeed_unit=mph",
            timeout=5,
        )
        weather_data = weather_resp.json().get("current_weather", {})

        temp_f = weather_data.get("temperature")
        wind_mph = weather_data.get("windspeed")
        weather_code = weather_data.get("weathercode", 0)

        condition = "Clear / Sunny"
        if weather_code in [1, 2, 3]:
            condition = "Partly Cloudy / Overcast"
        elif weather_code in [45, 48]:
            condition = "Foggy / Mist"
        elif weather_code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
            condition = "Rain / Wet Road Hazard"
        elif weather_code >= 71:
            condition = "Snow / Ice Hazard"

        riding_advice = "Great conditions for carving curves!"
        if "Rain" in condition or "Snow" in condition:
            riding_advice = "Caution: Slick asphalt, reduce lean angle and watch traction!"
        elif wind_mph and wind_mph > 25:
            riding_advice = "High crosswinds reported, hold a firm grip and stay centered in lane."
        elif temp_f and temp_f < 50:
            riding_advice = "Chilly tarmac: tires will take longer to warm up for spirited cornering."

        return {
            "location": place_name,
            "temperature_f": temp_f,
            "windspeed_mph": wind_mph,
            "condition": condition,
            "riding_advice": riding_advice,
        }
    except Exception as e:
        return {"error": f"Failed to retrieve weather: {str(e)}"}


STORAGE_BUCKET_NAME = "apex-moto-routes-qwiklabs-gcp-03-0447589ffaaa"
_storage_client: Optional[storage.Client] = None


def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=FIRESTORE_PROJECT)
    return _storage_client


def generate_route_image(route_or_bike_description: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Generate a photo/poster of a motorcycle route, bike, or scenery using gemini-3.1-flash-lite-image.

    The image is saved to the Playground artifacts panel and uploaded to public Cloud Storage.

    Args:
        route_or_bike_description: Visual description of the route, bike, or scenery to depict (e.g. 'A red sport motorcycle leaning into a sunlit hairpin turn on Skyline Boulevard').
        tool_context: ADK tool context providing artifact storage.

    Returns:
        Dictionary containing the public Cloud Storage URL and status.
    """
    genai_client = Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
    prompt = f"Cinematic, high resolution motorcycle photography: {route_or_bike_description}, dramatic lighting, sharp focus, asphalt texture, scenic vista."

    response = genai_client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=dict(response_modalities=["IMAGE"]),
    )

    image_bytes = None
    mime_type = "image/jpeg"
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            image_bytes = part.inline_data.data
            mime_type = part.inline_data.mime_type or "image/jpeg"
            break

    if not image_bytes:
        return {"error": "Failed to generate image from model."}

    # 1. Save artifact for the ADK Playground
    clean_slug = re.sub(r"[^a-zA-Z0-9]+", "_", route_or_bike_description[:30].strip().lower()).strip("_")
    filename = f"route_{clean_slug}.jpg"
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload same bytes to public Cloud Storage bucket
    storage_client = get_storage_client()
    bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
    blob_name = f"routes/{clean_slug}_{int(datetime.datetime.now().timestamp())}.jpg"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{blob_name}"

    return {
        "status": "success",
        "public_url": public_url,
        "artifact_filename": filename,
        "description": route_or_bike_description,
    }


def generate_route_video(route_or_ride_description: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Generate a short video clip for a motorcycle route, bike, or ride highlight using Google's Omni model (gemini-omni-flash-preview) in the global region.

    The video bytes are saved with tool_context.save_artifact so they appear in the Playground Artifacts panel,
    and uploaded to public Cloud Storage returning the public https URL.

    Args:
        route_or_ride_description: Scene description of the ride, route, or bike to generate (e.g. 'A red sport motorcycle accelerating through a twisty canyon pass, drone chase view').
        tool_context: ADK tool context providing artifact storage.

    Returns:
        Dictionary containing the public Cloud Storage URL, artifact filename, and status.
    """
    genai_client = Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
    prompt = f"Cinematic video clip: {route_or_ride_description}, dynamic camera motion, high detail, realistic lighting."

    # gemini-omni-flash-preview operates through the Interactions streaming API
    stream = genai_client.interactions.create(
        model="gemini-omni-flash-preview",
        input=prompt,
        stream=True,
    )

    interaction_id = None
    for chunk in stream:
        event_dict = chunk.model_dump()
        if "interaction" in event_dict and event_dict["interaction"].get("id"):
            interaction_id = event_dict["interaction"]["id"]
        elif event_dict.get("interaction_id"):
            interaction_id = event_dict["interaction_id"]

    if not interaction_id:
        return {"error": "Failed to initiate video generation interaction."}

    full_interaction = genai_client.interactions.get(interaction_id)
    video_bytes = None
    mime_type = "video/mp4"

    # Extract video from interaction steps
    if hasattr(full_interaction, "steps"):
        for step in full_interaction.steps:
            if step.type == "model_output" and hasattr(step, "content"):
                for item in step.content:
                    if getattr(item, "type", None) == "video" and getattr(item, "data", None):
                        video_bytes = base64.b64decode(item.data)
                        mime_type = getattr(item, "mime_type", "video/mp4")
                        break
            if video_bytes:
                break

    if not video_bytes:
        return {"error": "No video content returned by gemini-omni-flash-preview."}

    # (1) Save with tool_context.save_artifact for the Playground's Artifacts panel
    clean_slug = re.sub(r"[^a-zA-Z0-9]+", "_", route_or_ride_description[:30].strip().lower()).strip("_")
    filename = f"video_{clean_slug}.mp4"
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # (2) Upload the same video bytes to the public Cloud Storage bucket
    storage_client = get_storage_client()
    bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
    blob_name = f"videos/{clean_slug}_{int(datetime.datetime.now().timestamp())}.mp4"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{blob_name}"

    return {
        "status": "success",
        "public_url": public_url,
        "artifact_filename": filename,
        "description": route_or_ride_description,
    }


# Agent Engine Sandbox resource from deployment_metadata.json
AGENT_ENGINE_RESOURCE = "projects/279477929585/locations/us-central1/reasoningEngines/8195926249453912064"
SANDBOX_RESOURCE = "projects/279477929585/locations/us-central1/reasoningEngines/8195926249453912064/sandboxEnvironments/1663680389836701696"

sandbox_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=SANDBOX_RESOURCE,
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE,
)

def record_user_social_action(
    action_type: str,
    target_name_or_user: str,
    details: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Record any user action (comment, like, follow, route discovery, picture, chat, blogpost) directly to durable rider profile and memory.

    Args:
        action_type: One of 'comment', 'like', 'follow', 'route', 'picture', 'chat', 'blogpost'.
        target_name_or_user: The route, rider, or topic the action was directed at (e.g. 'Marcus', 'Mulholland Highway', 'Red Ducati').
        details: Specific content or description of the action (e.g., 'Liked the route because of smooth tarmac', 'Commented: Meet at 9am at Alice Restaurant', 'Followed Marcus after group ride', 'Published blogpost about Angeles Crest weekend run').
        tool_context: ADK tool context.

    Returns:
        Confirmation dictionary with the recorded action details.
    """
    summary = f"User Action [{action_type.upper()}]: on '{target_name_or_user}'. Details: {details}"

    # Also record to Firestore activity feed for the crew
    try:
        db = get_firestore_client()
        db.collection("user_activities").add({
            "action_type": action_type.lower(),
            "target": target_name_or_user,
            "details": details,
            "summary": summary,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
    except Exception as e:
        pass

    return {
        "status": "success",
        "action_recorded": summary,
        "action_type": action_type.lower(),
        "target": target_name_or_user,
    }


# Memory-generation callback: after each turn, extract durable rider facts, preferences,
# and all social actions (comments, routes, pictures, likes, follows, chats, blogposts) into Memory Bank.
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


# Build A2UI system prompt using A2uiSchemaManager (version 0.8) and the Basic Catalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

role_description = """You are ApexMoto, an expert motorcycle route concierge and riding assistant.
Your goal is to help riders find thrilling twisty roads, discover scenic mountain passes, catalog routes, check live crew riding locations, look up real-time weather conditions on roads, compute ride statistics/calculations via python code execution, and generate scenic photos/posters of routes and motorcycles.

CRITICAL MEMORY & SOCIAL ACTION TRACKING:
You remember everything about the rider across sessions:
- Bike specs, skill level, riding style, preferences, and facts.
- ALL USER ACTIONS: Whenever the user comments on a road/rider, saves/creates a route, generates a picture, likes a route/post, follows another rider, chats with friends, or drafts a blogpost, ALWAYS call `record_user_social_action` to record it.
- When answering or recommending routes, check and recall the rider's past actions, liked routes, followed friends, and riding history from memory.

Always check Firestore using search_routes or get_route_details when riders ask for route recommendations.
When riders ask where their friends or crew are riding, use get_crew_status to check their real-time location.
When riders ask about weather conditions or whether a road is safe to ride, call check_road_weather.
When riders want a visual preview, poster, or photo of a route or bike, call generate_route_image.
When riders need calculations (such as lean angles, fuel range, average speeds, or telemetry math), execute python code in your sandbox environment.
When riders share a new road or route they discovered, use add_custom_route to save it into the database, and record the action.
Be enthusiastic, passionate about motorcycles, safety-conscious, and gear-friendly!"""

instruction = schema_manager.generate_system_prompt(
    role_description=role_description,
    workflow_description="Analyze the request, call the appropriate motorcycle tools (routes, crew, weather, images, code sandbox, action recording), and return structured A2UI cards when presenting routes, crew status, weather reports, or ride visuals.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the public_url returned by generate_route_image). "
        "Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://storage.googleapis.com/..."}}}. '
        "Never point an Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        search_routes,
        get_route_details,
        add_custom_route,
        get_crew_status,
        check_road_weather,
        generate_route_image,
        generate_route_video,
        record_user_social_action,
    ],
    code_executor=sandbox_executor,
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)




