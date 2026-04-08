# NextGenGolf (React)

This project has been refactored into a **local React app** focused on transparent bucket-by-bucket ranking.

## What changed

- The app now runs in the browser on your laptop with Vite + React.
- Every bucket ranks players **#1 through #5**.
- Each ranked player includes plain-English **reasons** that explain the ranking.
- A built-in "How to use this app" section explains the workflow from bucket selection to lineup building.

## Run locally

```bash
npm install
npm run dev
```

Then open the local URL printed by Vite (normally `http://localhost:5173`).

## Build for production

```bash
npm run build
npm run preview
```

## Ranking logic (high-level)

Players are scored inside each bucket using weighted metrics:

- Cut rate
- Top-10 odds
- SG: Approach
- Bogey avoidance
- Double-bogey rate (penalized when high)
- Masters history
- Augusta-correlated form
- Recent finishes

The app normalizes these metrics **within each bucket**, computes a weighted score, sorts players, and generates reasons from each player's strongest and weakest drivers.

## Data source

- App runtime CSV: `public/data/masters_players_real.csv`
- Original source CSV retained: `data/masters_players_real.csv`
