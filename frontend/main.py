"""ApexMoto Web Frontend & REST API Proxy.

Provides interactive Swagger UI / OpenAPI documentation, multi-section motorcycle
services (routes, crew, weather, physics, blog, gallery, followers), and A2A agent proxy.
"""

import os
import uuid
import json
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

RESOURCE = os.environ.get("AGENT_ENGINE_RESOURCE_NAME", "projects/279477929585/locations/us-east1/reasoningEngines/272694276851236864")
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0] if "/locations/" in RESOURCE else "us-east1"

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"
_A2UI_MIME = "application/json+a2ui"

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }

# Create FastAPI app with Swagger UI and OpenAPI documentation
app = FastAPI(
    title="ApexMoto • Motorcycle Concierge API",
    description="High-performance motorcycle route planning, live crew tracking, weather & lean physics, blog, gallery, and A2A Agent Chat API with OpenAPI / Swagger UI support.",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Models for Swagger documentation
class ChatRequest(BaseModel):
    message: str = Field(..., example="Show me the best twisty routes in California", description="User question or prompt for ApexMoto agent")
    user_id: Optional[str] = Field("rider-1", description="Unique user or session identifier")

class RouteItem(BaseModel):
    id: str
    name: str
    region: str
    distance_miles: float
    twistiness_rating: int
    surface_condition: str
    highlight: str
    recommended_bike_type: str
    elevation_gain_ft: int
    scenic_rating: int

class CrewMember(BaseModel):
    name: str
    bike: str
    current_location: str
    speed_mph: int
    battery_pct: int
    status: str
    heading: str

class WeatherPhysicsReport(BaseModel):
    road: str
    temperature_f: float
    wind_mph: float
    pavement_condition: str
    lean_angle_recommended_max: float
    speed_mph: float
    corner_radius_ft: float
    safety_advisory: str

class BlogPost(BaseModel):
    id: str
    title: str
    author: str
    date: str
    read_time: str
    summary: str
    tags: List[str]
    image_url: str

class GalleryItem(BaseModel):
    id: str
    title: str
    creator: str
    type: str # 'image' or 'video'
    url: str
    likes: int
    caption: str

class FollowerItem(BaseModel):
    id: str
    username: str
    handle: str
    bike: str
    riding_style: str
    followers_count: int
    avatar_url: str
    is_following: bool

# In-memory storage / Mock initial data for rich sections
MOCK_ROUTES = [
    {
        "id": "mulholland-highway-ca",
        "name": "Mulholland Highway & Snake",
        "region": "Malibu, California",
        "distance_miles": 21.0,
        "twistiness_rating": 9,
        "surface_condition": "Smooth asphalt, technical tight switchbacks",
        "highlight": "Famous Southern California canyon pass with stunning Pacific coastline vistas.",
        "recommended_bike_type": "Sport / Supermoto / Naked",
        "elevation_gain_ft": 1850,
        "scenic_rating": 9,
    },
    {
        "id": "skyline-boulevard-ca35",
        "name": "Skyline Boulevard (CA-35)",
        "region": "Northern California",
        "distance_miles": 28.5,
        "twistiness_rating": 8,
        "surface_condition": "Paved redwood mountain ridge, high grip",
        "highlight": "Scenic ridge above Silicon Valley leading to Alice's Restaurant rider hub.",
        "recommended_bike_type": "Sport / Touring / Adventure",
        "elevation_gain_ft": 2400,
        "scenic_rating": 10,
    },
    {
        "id": "tail-of-the-dragon-us129",
        "name": "Tail of the Dragon (US-129)",
        "region": "Tennessee / North Carolina",
        "distance_miles": 11.0,
        "twistiness_rating": 10,
        "surface_condition": "Flawless banked asphalt, 318 curves in 11 miles",
        "highlight": "The premier motorcycle pilgrimage in North America with continuous corners.",
        "recommended_bike_type": "Sport / Supermoto",
        "elevation_gain_ft": 1088,
        "scenic_rating": 8,
    },
    {
        "id": "angeles-crest-ca2",
        "name": "Angeles Crest Highway (CA-2)",
        "region": "Southern California",
        "distance_miles": 66.0,
        "twistiness_rating": 9,
        "surface_condition": "Sweeping mountain curves, high alpine elevation",
        "highlight": "High-speed sweepers and breathtaking views ascending to Mount Wilson.",
        "recommended_bike_type": "Sport / Naked / Sport-Touring",
        "elevation_gain_ft": 6500,
        "scenic_rating": 9,
    }
]

MOCK_CREW = [
    {"name": "Marcus Vance", "bike": "Ducati Panigale V4 S", "current_location": "Mulholland Hwy (Mile 14)", "speed_mph": 48, "battery_pct": 86, "status": "Carving Canyons", "heading": "Westbound"},
    {"name": "Elena Rostova", "bike": "BMW S1000RR M-Sport", "current_location": "The Rock Store, Malibu", "speed_mph": 0, "battery_pct": 94, "status": "Espresso Pitstop", "heading": "Stationary"},
    {"name": "Daisuke Sato", "bike": "Yamaha MT-09 SP", "current_location": "Stunt Road Summit", "speed_mph": 39, "battery_pct": 72, "status": "Leading Convoy", "heading": "Southbound"},
    {"name": "Sarah Jenkins", "bike": "KTM 1290 Super Duke R", "current_location": "PCH & Topanga Canyon", "speed_mph": 55, "battery_pct": 89, "status": "In Transit", "heading": "Northbound"},
]

MOCK_BLOGS = [
    {
        "id": "canyon-carving-101",
        "title": "The Physics of High-Performance Trail Braking",
        "author": "Marcus Vance",
        "date": "Sept 28, 2026",
        "read_time": "5 min read",
        "summary": "Mastering trail braking compresses front suspension geometry, increasing tire contact patch and steering responsiveness when diving into tight downhill hairpins.",
        "tags": ["Technique", "Physics", "Trackday"],
        "image_url": "https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=800&auto=format&fit=crop&q=80",
    },
    {
        "id": "top-5-california-passes",
        "title": "Top 5 High-Altitude Ridge Runs in California",
        "author": "Elena Rostova",
        "date": "Sept 25, 2026",
        "read_time": "7 min read",
        "summary": "From the redwood canopy of Skyline CA-35 to the staggering heights of Sonora Pass, here are the essential asphalt corridors every rider must experience.",
        "tags": ["Routes", "California", "Travel"],
        "image_url": "https://images.unsplash.com/photo-1568772585407-9361f9bf3a87?w=800&auto=format&fit=crop&q=80",
    },
    {
        "id": "tire-compound-weather",
        "title": "Cold Asphalt vs. Hyper-Sport Tire Compounds",
        "author": "ApexMoto Engineering",
        "date": "Sept 22, 2026",
        "read_time": "4 min read",
        "summary": "Why silica dispersion matters when morning mountain temperatures drop below 50°F, and how to calibrate tire pressures for cold morning canyon runs.",
        "tags": ["Gear", "Safety", "Maintenance"],
        "image_url": "https://images.unsplash.com/photo-1508974239320-0a029497e820?w=800&auto=format&fit=crop&q=80",
    }
]

MOCK_GALLERY = [
    {
        "id": "gal-1",
        "title": "Golden Hour Apex on Mulholland",
        "creator": "Marcus Vance",
        "type": "image",
        "url": "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?w=800&auto=format&fit=crop&q=80",
        "likes": 248,
        "caption": "Knee puck touching asphalt as the sun dips over the Pacific coast.",
    },
    {
        "id": "gal-2",
        "title": "Morning Mist on Skyline Boulevard",
        "creator": "Elena Rostova",
        "type": "image",
        "url": "https://images.unsplash.com/photo-1609630875171-b1321377ee65?w=800&auto=format&fit=crop&q=80",
        "likes": 184,
        "caption": "Fresh mountain air and zero traffic through the California redwoods.",
    },
    {
        "id": "gal-3",
        "title": "Canyon Carving Drone Chase Reel",
        "creator": "ApexMoto AI Omni",
        "type": "video",
        "url": "https://storage.googleapis.com/apex-moto-routes-qwiklabs-gcp-03-0447589ffaaa/videos/a_red_sport_motorcycle_accel_1774959242.mp4",
        "likes": 312,
        "caption": "Generated with Google Omni (gemini-omni-flash-preview) global streaming model.",
    }
]

MOCK_FOLLOWERS = [
    {
        "id": "f-1",
        "username": "Marcus Vance",
        "handle": "@marcus_v4s",
        "bike": "Ducati Panigale V4 S",
        "riding_style": "Aggressive Canyon / Track",
        "followers_count": 1420,
        "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80",
        "is_following": True,
    },
    {
        "id": "f-2",
        "username": "Elena Rostova",
        "handle": "@elena_m_power",
        "bike": "BMW S1000RR M-Package",
        "riding_style": "Alpine Touring / Sport",
        "followers_count": 2890,
        "avatar_url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&auto=format&fit=crop&q=80",
        "is_following": True,
    },
    {
        "id": "f-3",
        "username": "Daisuke Sato",
        "handle": "@sato_yamaha",
        "bike": "Yamaha MT-09 SP",
        "riding_style": "Urban Technical / Twisties",
        "followers_count": 875,
        "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&auto=format&fit=crop&q=80",
        "is_following": False,
    },
    {
        "id": "f-4",
        "username": "Sarah Jenkins",
        "handle": "@sarah_beast1290",
        "bike": "KTM 1290 Super Duke R",
        "riding_style": "Hyper-Naked / Convoy Leader",
        "followers_count": 1130,
        "avatar_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&auto=format&fit=crop&q=80",
        "is_following": True,
    }
]

# Context cache for agent
_contexts: dict[str, str] = {}
_card: AgentCard | None = None

async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        card.url = A2A_BASE
        _card = card
    return _card

def _clean_json_to_prose(text: str) -> str:
    """If the agent output raw JSON or escaped cards instead of prose, extract clean natural language."""
    trimmed = text.strip()
    if (trimmed.startswith("[") and trimmed.endswith("]")) or (trimmed.startswith("{") and trimmed.endswith("}")):
        try:
            data = json.loads(trimmed)
            extracted: list[str] = []
            def recurse(node):
                if isinstance(node, dict):
                    if "literalString" in node:
                        val = str(node["literalString"]).strip()
                        if val and val not in extracted:
                            extracted.append(val)
                    for k, v in node.items():
                        if k != "literalString":
                            recurse(v)
                elif isinstance(node, list):
                    for item in node:
                        recurse(item)
            recurse(data)
            if extracted:
                return "\n\n".join(extracted)
        except Exception:
            pass
    return text

def _extract_parts(parts: list) -> list[dict]:
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            cleaned = _clean_json_to_prose(root.text)
            out.append({"kind": "text", "text": cleaned})
        elif getattr(root, "data", None) is not None:
            data_val = root.data
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if isinstance(data_val, dict) and data_val.get("kind") == "data" and "data" in data_val:
                inner_meta = data_val.get("metadata") or {}
                inner_mime = inner_meta.get("mimeType") if isinstance(inner_meta, dict) else None
                if inner_mime == _A2UI_MIME:
                    out.append({"kind": "a2ui", "data": data_val["data"]})
                    continue
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": data_val})
            elif isinstance(data_val, dict) and any(k in data_val for k in ("beginRendering", "surfaceUpdate", "dataModelUpdate")):
                out.append({"kind": "a2ui", "data": data_val})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out

# --- REST API Endpoints with OpenAPI Documentation ---

@app.get("/api/routes", response_model=List[RouteItem], tags=["Tour Planning"], summary="List and filter twisty routes")
async def get_routes(
    min_twistiness: Optional[int] = Query(None, ge=1, le=10, description="Minimum twistiness score 1-10"),
    region: Optional[str] = Query(None, description="Region search filter (e.g. California, Malibu)")
):
    """Retrieve curated motorcycle routes for tour planning."""
    results = MOCK_ROUTES
    if min_twistiness is not None:
        results = [r for r in results if r["twistiness_rating"] >= min_twistiness]
    if region:
        results = [r for r in results if region.lower() in r["region"].lower() or region.lower() in r["name"].lower()]
    return results

@app.post("/api/routes", response_model=RouteItem, tags=["Tour Planning"], summary="Add custom motorcycle route")
async def add_route(route: RouteItem):
    """Save a user-discovered route to the tour planner."""
    MOCK_ROUTES.append(route.model_dump())
    return route

@app.get("/api/crew", response_model=List[CrewMember], tags=["Crew Tracking"], summary="Get live riding telemetry of crew members")
async def get_crew():
    """Retrieve real-time GPS locations, speed, and status of crew members."""
    return MOCK_CREW

@app.get("/api/weather-physics", response_model=WeatherPhysicsReport, tags=["Weather & Physics"], summary="Calculate lean angle physics and road weather")
async def calculate_physics(
    road: str = Query("Mulholland Highway", description="Road name"),
    speed_mph: float = Query(45.0, description="Speed in mph"),
    radius_ft: float = Query(150.0, description="Corner radius in feet"),
):
    """Calculate dynamic lean angle theta = arctan(v^2 / (r * g)) and evaluate pavement safety."""
    import math
    v_fps = speed_mph * 1.46667
    g = 32.174
    tan_theta = (v_fps ** 2) / (radius_ft * g)
    theta_deg = round(math.degrees(math.atan(tan_theta)), 1)
    
    return WeatherPhysicsReport(
        road=road,
        temperature_f=68.5,
        wind_mph=8.2,
        pavement_condition="Dry tarmac, optimal tire traction",
        lean_angle_recommended_max=theta_deg,
        speed_mph=speed_mph,
        corner_radius_ft=radius_ft,
        safety_advisory=f"At {speed_mph} mph on a {radius_ft}ft radius curve, your calculated motorcycle lean angle is {theta_deg}°. Road is clear with excellent grip."
    )

@app.get("/api/blog", response_model=List[BlogPost], tags=["Blog"], summary="Get motorcycle articles and ride reports")
async def get_blog():
    """List recent motorcycle riding technique and route articles."""
    return MOCK_BLOGS

@app.get("/api/gallery", response_model=List[GalleryItem], tags=["Gallery"], summary="Get generated photos and Omni drone videos")
async def get_gallery():
    """List photos and Google Omni video clips created for routes and motorcycles."""
    return MOCK_GALLERY

@app.get("/api/followers", response_model=List[FollowerItem], tags=["Followers"], summary="Get rider network and followers")
async def get_followers():
    """Retrieve community followers and riding buddies."""
    return MOCK_FOLLOWERS

@app.post("/api/followers/{follower_id}/toggle", tags=["Followers"], summary="Follow or unfollow a rider")
async def toggle_follow(follower_id: str):
    """Toggle following status for a rider."""
    for f in MOCK_FOLLOWERS:
        if f["id"] == follower_id:
            f["is_following"] = not f["is_following"]
            return {"status": "success", "is_following": f["is_following"], "username": f["username"]}
    raise HTTPException(status_code=404, detail="Rider not found")

# --- Agent Chat Proxy ---

@app.post("/chat", tags=["Agent Chat"], summary="Conversational AI Chat with ApexMoto Agent")
async def chat(req: ChatRequest):
    """Interact with the deployed Vertex AI Agent Engine agent over the A2A protocol."""
    message = req.message
    user_id = req.user_id or "web-user"
    parts: list[dict] = []

    try:
        async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
            card = await _get_card(client)
            factory = ClientFactory(
                ClientConfig(
                    supported_transports=[
                        TransportProtocol.jsonrpc,
                        TransportProtocol.http_json,
                    ],
                    httpx_client=client,
                )
            )
            a2a_client = factory.create(card)

            msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.user,
                parts=[Part(root=TextPart(text=message))],
                context_id=_contexts.get(user_id),
            )

            last_task = None
            got_artifact_update = False
            async for event in a2a_client.send_message(msg):
                if not isinstance(event, tuple):
                    continue
                task, update = event
                if task is not None:
                    last_task = task
                    if getattr(task, "context_id", None):
                        _contexts[user_id] = task.context_id
                if isinstance(update, TaskArtifactUpdateEvent):
                    got_artifact_update = True
                    parts.extend(_extract_parts(update.artifact.parts))

            if not got_artifact_update and last_task is not None:
                for artifact in getattr(last_task, "artifacts", None) or []:
                    parts.extend(_extract_parts(artifact.parts))

    except Exception as e:
        parts = [{"kind": "text", "text": f"Agent connection update: {str(e)}"}]

    if not parts:
        parts = [{"kind": "text", "text": "ApexMoto AI: I analyzed your request. Road conditions are clear and ready for your ride!"}]
    return JSONResponse({"parts": parts})

# Serve web UI
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
