# Cost Decisions Log

> All decisions that involve potential cost are recorded here.
> Free-tier limits verified as of 2026-10-09. Re-confirm at signup — providers change terms.

## Free-Tier Services in Use

| Service | Free Allowance | Watch-outs | Decision |
|---|---|---|---|
| Render Free | 750 instance-hours/month, 512 MB RAM, ~0.1 CPU, ~5 GB bandwidth | Spins down after 15 min idle (30–60 s cold start) | **Use** — acceptable for pilot/demo |
| Neon Free | ~0.5 GB storage, ~100 compute-hours/month, scale-to-zero | First query after idle is slow | **Use** — PostGIS supported; photos stored outside DB |
| Firebase Spark | Email/social sign-in free to ~50k MAU; FCM free | Phone auth is metered | **Use** — email/Google auth for MVP |
| Vercel Hobby | ~100 GB bandwidth/month, 1M function invocations | Non-commercial use only | **Use** — pilot/demo; upgrade before commercial launch |
| Twilio trial | ~100 SMS units | No true free tier | **Use with hard SMS_DAILY_CAP=20** — push is primary |
| OSRM, OSM, PostGIS, OR-Tools, MCP SDK | Free and open source | Attribution required | **Use** |
| Mapbox | 50k GL JS map loads/month | Optional | **Optional** — default is free OSM tiles |

## Pending Decisions

| Decision | Trigger | Notes |
|---|---|---|
| OSRM hosting | Phase 7 | Self-hosted on Render costs ~$5–7/month outside free tier; estimate fallback is free |
| Vercel upgrade | Before any commercial launch | Hobby plan is non-commercial |
| LLM provider & tier | Phase 9 | Cheapest capable tier; budget-capped via AGENT_MAX_CALLS_PER_DAY |

## Approved Deviations & Phase 13 Confirmations

| Decision | Date | Rationale | Cost Impact |
|---|---|---|---|
| OSRM Estimate Fallback for Pilot | 2026-11-08 | Use straight-line PostGIS ST_Distance + speed matrix fallback (`OSRM_FALLBACK_TO_ESTIMATE=true`) instead of self-hosting dedicated OSRM container on Render. | $0.00 / month (saved $5–7/month) |
| CV Memory Optimization on Render Free | 2026-11-08 | Disabled TTA in production (`TTA=false`) and tuned ONNX thread count (`intra_op_num_threads=2`) to guarantee RSS < 320 MB within Render's 512 MB ceiling. | $0.00 / month (no need for paid instance) |
| Vercel SPA Dashboard on Hobby Plan | 2026-11-08 | Vite React dashboard hosted on Vercel Hobby tier for community pilot; commercial license upgrade triggered before public monetization. | $0.00 / month |
| Neon Serverless Connection Pooling | 2026-11-08 | Utilized `-pooler` connection string with `pool_size=5` and `pool_pre_ping=True` to smoothly accommodate scale-to-zero compute spin-down without connection exhaustion. | $0.00 / month |

