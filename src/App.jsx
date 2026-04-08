import { useEffect, useMemo, useState } from 'react';
import Papa from 'papaparse';
import { rankPlayersByBucket } from './ranking';

const CSV_PATH = '/data/masters_players_real.csv';

export default function App() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  useEffect(() => {
    Papa.parse(CSV_PATH, {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        setRows(results.data ?? []);
      },
      error: (err) => {
        setError(err.message);
      }
    });
  }, []);

  const rankedBuckets = useMemo(() => rankPlayersByBucket(rows), [rows]);

  const filteredBuckets = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) return rankedBuckets;

    return rankedBuckets
      .map((bucket) => ({
        ...bucket,
        players: bucket.players.filter((player) => player.name.toLowerCase().includes(trimmed))
      }))
      .filter((bucket) => bucket.players.length > 0);
  }, [rankedBuckets, query]);

  return (
    <main className="app-shell">
      <header>
        <h1>NextGenGolf Group Rankings</h1>
        <p>
          Every bucket now shows a transparent ranking from 1-5 with the strongest and weakest drivers for each player.
        </p>
      </header>

      <section className="card how-to">
        <h2>How to use this app</h2>
        <ol>
          <li>Start in Bucket 1 and move downward. Each player is ranked #1 (best) to #5 within that bucket.</li>
          <li>Read the “Reasons” column to understand exactly why a player was ranked where they were.</li>
          <li>Build your lineup by taking your preferred player from each bucket (13 total picks).</li>
          <li>Use the search bar if you want to quickly inspect a specific golfer across all buckets.</li>
        </ol>
      </section>

      <section className="card search-row">
        <label htmlFor="nameQuery">Filter players by name</label>
        <input
          id="nameQuery"
          type="text"
          placeholder="Type a player name..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </section>

      {error && <p className="error">Could not load player CSV: {error}</p>}

      <section className="groups-grid">
        {filteredBuckets.map((bucket) => (
          <article className="card" key={bucket.bucket}>
            <h3>Bucket {bucket.bucket}</h3>
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Player</th>
                  <th>Score</th>
                  <th>Reasons</th>
                </tr>
              </thead>
              <tbody>
                {bucket.players.map((player) => (
                  <tr key={player.player_id} className={player.rank === 1 ? 'top-row' : ''}>
                    <td>#{player.rank}</td>
                    <td>{player.name}</td>
                    <td>{player.score.toFixed(3)}</td>
                    <td>
                      <ul>
                        {player.reasons.map((reason) => (
                          <li key={`${player.player_id}-${reason}`}>{reason}</li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </article>
        ))}
      </section>
    </main>
  );
}
