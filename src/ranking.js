const METRIC_CONFIG = {
  cut_rate: { label: 'Cut-Making Rate', weight: 0.22, higherIsBetter: true },
  odds_top10: { label: 'Top-10 Odds', weight: 0.18, higherIsBetter: true },
  sg_approach: { label: 'SG: Approach', weight: 0.16, higherIsBetter: true },
  bogey_avoidance: { label: 'Bogey Avoidance', weight: 0.11, higherIsBetter: true },
  double_bogey_rate: { label: 'Double-Bogey Rate', weight: 0.08, higherIsBetter: false },
  masters_history: { label: 'Masters History', weight: 0.1, higherIsBetter: true },
  augusta_correlated: { label: 'Augusta-Correlated Form', weight: 0.07, higherIsBetter: true },
  recent_finishes_score: { label: 'Recent Form', weight: 0.08, higherIsBetter: true }
};

const parseNumber = (value) => {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const buildRecentFormScore = (recentFinishesText) => {
  if (!recentFinishesText) return 0;

  const finishes = recentFinishesText
    .split(';')
    .map((finish) => Number.parseInt(finish, 10))
    .filter((finish) => Number.isFinite(finish) && finish > 0);

  if (!finishes.length) return 0;

  const averageFinish = finishes.reduce((sum, finish) => sum + finish, 0) / finishes.length;
  return -averageFinish;
};

const normalizeMetric = (players, metricKey, higherIsBetter = true) => {
  const values = players.map((player) => player[metricKey]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min;

  return players.map((player) => {
    if (span === 0) return 0.5;
    const scaled = (player[metricKey] - min) / span;
    return higherIsBetter ? scaled : 1 - scaled;
  });
};

const formatReason = (metricLabel, normalizedValue) => {
  if (normalizedValue >= 0.8) return `Elite ${metricLabel.toLowerCase()} compared with this group.`;
  if (normalizedValue >= 0.65) return `Strong ${metricLabel.toLowerCase()} versus other players in this group.`;
  if (normalizedValue <= 0.2) return `${metricLabel} is a key weakness versus this group.`;
  return `${metricLabel} is near the middle of this group.`;
};

export const rankPlayersByBucket = (rawPlayers) => {
  const players = rawPlayers.map((player) => ({
    ...player,
    bucket: Number.parseInt(player.bucket, 10),
    cut_rate: parseNumber(player.cut_rate),
    odds_top10: parseNumber(player.odds_top10),
    sg_approach: parseNumber(player.sg_approach),
    bogey_avoidance: parseNumber(player.bogey_avoidance),
    double_bogey_rate: parseNumber(player.double_bogey_rate),
    masters_history: parseNumber(player.masters_history),
    augusta_correlated: parseNumber(player.augusta_correlated),
    recent_finishes_score: buildRecentFormScore(player.recent_finishes)
  }));

  const grouped = new Map();
  players.forEach((player) => {
    if (!grouped.has(player.bucket)) grouped.set(player.bucket, []);
    grouped.get(player.bucket).push(player);
  });

  return Array.from(grouped.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([bucket, bucketPlayers]) => {
      const normalized = Object.entries(METRIC_CONFIG).reduce((acc, [metric, cfg]) => {
        acc[metric] = normalizeMetric(bucketPlayers, metric, cfg.higherIsBetter);
        return acc;
      }, {});

      const scoredPlayers = bucketPlayers
        .map((player, index) => {
          const metricBreakdown = Object.entries(METRIC_CONFIG).map(([metric, cfg]) => {
            const value = normalized[metric][index];
            return {
              metric,
              label: cfg.label,
              weight: cfg.weight,
              normalizedValue: value,
              contribution: value * cfg.weight
            };
          });

          const score = metricBreakdown.reduce((sum, item) => sum + item.contribution, 0);
          const strongest = [...metricBreakdown].sort((a, b) => b.contribution - a.contribution).slice(0, 2);
          const weakest = [...metricBreakdown].sort((a, b) => a.normalizedValue - b.normalizedValue)[0];

          return {
            ...player,
            score,
            reasons: [
              ...strongest.map((item) => formatReason(item.label, item.normalizedValue)),
              formatReason(weakest.label, weakest.normalizedValue)
            ]
          };
        })
        .sort((a, b) => b.score - a.score)
        .map((player, rank) => ({
          ...player,
          rank: rank + 1
        }));

      return {
        bucket,
        players: scoredPlayers
      };
    });
};
