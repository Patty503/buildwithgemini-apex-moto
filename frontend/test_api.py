"""Automated Test Suite for ApexMoto Frontend & API Gateway.

Validates:
1. OpenAPI specification and Swagger UI docs availability.
2. Multi-section REST endpoints:
   - /api/routes (filtering by twistiness & region)
   - /api/crew (telemetry metrics & convoy statuses)
   - /api/weather-physics (lean angle calculation: theta = arctan(v^2 / (r * g)))
   - /api/blog (article listings)
   - /api/gallery (visual assets & Omni video items)
   - /api/followers (retrieval and follow/unfollow toggle)
3. Natural Language extraction & formatting.
"""

import pytest
import math
from fastapi.testclient import TestClient
from main import app, _clean_json_to_prose

client = TestClient(app)

def test_openapi_docs():
    """Verify OpenAPI 3.1 JSON schema and Swagger UI endpoint."""
    res = client.get("/openapi.json")
    assert res.status_code == 200
    data = res.json()
    assert data["info"]["title"] == "ApexMoto • Motorcycle Concierge API"
    assert "/api/routes" in data["paths"]
    assert "/api/crew" in data["paths"]
    assert "/api/weather-physics" in data["paths"]
    assert "/chat" in data["paths"]

    docs_res = client.get("/docs")
    assert docs_res.status_code == 200
    assert "swagger-ui" in docs_res.text.lower()

def test_routes_endpoint():
    """Verify Tour Planning route retrieval and filtering."""
    res = client.get("/api/routes")
    assert res.status_code == 200
    routes = res.json()
    assert len(routes) >= 4
    first = routes[0]
    assert "name" in first
    assert "twistiness_rating" in first

    # Test filtering by twistiness
    filter_res = client.get("/api/routes?min_twistiness=10")
    assert filter_res.status_code == 200
    high_twist = filter_res.json()
    assert len(high_twist) >= 1
    for r in high_twist:
        assert r["twistiness_rating"] >= 10

def test_crew_telemetry_endpoint():
    """Verify Live Crew Radar and real-time telemetry."""
    res = client.get("/api/crew")
    assert res.status_code == 200
    crew = res.json()
    assert len(crew) >= 4
    names = [c["name"] for c in crew]
    assert "Marcus Vance" in names
    assert "Elena Rostova" in names
    for c in crew:
        assert "speed_mph" in c
        assert "battery_pct" in c
        assert "status" in c

def test_weather_and_physics_endpoint():
    """Verify Lean Angle calculations in sandbox environment: theta = arctan(v^2 / (r * g))."""
    speed_mph = 45.0
    radius_ft = 150.0
    res = client.get(f"/api/weather-physics?road=Mulholland&speed_mph={speed_mph}&radius_ft={radius_ft}")
    assert res.status_code == 200
    data = res.json()
    assert data["road"] == "Mulholland"
    
    # Calculate expected lean angle manually
    v_fps = speed_mph * 1.46667
    g = 32.174
    tan_theta = (v_fps ** 2) / (radius_ft * g)
    expected_theta = round(math.degrees(math.atan(tan_theta)), 1)
    
    assert data["lean_angle_recommended_max"] == expected_theta
    assert "safety_advisory" in data

def test_blog_and_gallery_endpoints():
    """Verify media and knowledge blog endpoints."""
    res_blog = client.get("/api/blog")
    assert res_blog.status_code == 200
    blogs = res_blog.json()
    assert len(blogs) >= 3

    res_gal = client.get("/api/gallery")
    assert res_gal.status_code == 200
    gallery = res_gal.json()
    assert len(gallery) >= 3
    types = [g["type"] for g in gallery]
    assert "video" in types
    assert "image" in types

def test_followers_and_toggle_action():
    """Verify follower network and interactive toggle mechanism."""
    res = client.get("/api/followers")
    assert res.status_code == 200
    followers = res.json()
    assert len(followers) >= 4
    target = followers[0]
    target_id = target["id"]
    initial_status = target["is_following"]

    # Toggle follow state
    toggle_res = client.post(f"/api/followers/{target_id}/toggle")
    assert toggle_res.status_code == 200
    toggle_data = toggle_res.json()
    assert toggle_data["status"] == "success"
    assert toggle_data["is_following"] == (not initial_status)

    # Toggle back to restore initial state
    restore_res = client.post(f"/api/followers/{target_id}/toggle")
    assert restore_res.status_code == 200
    assert restore_res.json()["is_following"] == initial_status

def test_clean_json_to_prose():
    """Verify natural language conversion from raw A2UI JSON structures."""
    raw_json = '[{"beginRendering": {"root": "c1"}}, {"surfaceUpdate": {"components": [{"id": "t1", "component": {"Text": {"text": {"literalString": "Mulholland Highway is clear and dry."}}}}]}}]'
    prose = _clean_json_to_prose(raw_json)
    assert "Mulholland Highway is clear and dry." in prose
    assert "{" not in prose
    assert "beginRendering" not in prose

    normal_text = "Good morning rider! The mountain pass is looking clear today."
    assert _clean_json_to_prose(normal_text) == normal_text
