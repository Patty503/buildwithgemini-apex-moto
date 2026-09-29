# My agent: ApexMoto (MotoRide Crew Agent)
One-liner: A conversational agent that helps motorcycle riders discover twisty routes, track and coordinate live group rides, and automatically generate telemetry-rich ride stories and highlight visuals from their trips.

Tool coverage:
- Memory: Remembers rider profile, bike type/specs, riding style (cruiser vs. canyon carver), favorite road surfaces, friend list, and past tour history/preferences.
- Tools:
  - Route discovery & twisty road finder (curated road database by twistiness rating, elevation, surface condition, and weather)
  - Live rider crew tracker (fetch friends' live GPS statuses, active convoy checkpoints, and group meetup points)
  - Telemetry & ride story generator (processes ride logs: max speed, max lean angle, total distance, elevation profile, and drafts AI-narrated ride blogs/posts)
- Catalog/UI: Curated scenic routes, twisty pass listings, active group ride cards, and rider profile cards rendered via A2UI.
- Image gen: Generates scenic ride route highlight posters, dramatic bike snapshot art along route landmarks, or route banner previews.
- Sandbox: Computes ride statistics, lean angle calculations, route elevation delta, average pace, and fuel range estimates based on bike consumption.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Code sandbox for telemetry analysis (speed/lean angle stats), Google Maps API integration for live coordinate mapping, and multimodal video generation (Omni) for ride highlight clips.
