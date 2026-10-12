-- SQLite examples. These are reproducible descriptive queries, not scouting verdicts.
-- 1. Audit historical coverage and source freshness by league-season.
SELECT league, season, COUNT(*) AS fixtures,
       SUM(home_goals IS NOT NULL) AS results,
       MAX(CASE WHEN home_goals IS NOT NULL THEN date END) AS latest_result
FROM results GROUP BY league,season ORDER BY league,season DESC;

-- 2. Historical midfielders with meaningful observed minutes.
-- Compare only within one dataset; these are provider-selected match samples.
SELECT dataset,player,team,minutes,matches,
       ROUND(90.0*key_passes/NULLIF(minutes,0),2) AS key_passes_per90,
       ROUND(90.0*progressive_passes/NULLIF(minutes,0),2) AS progressive_passes_per90
FROM event_players WHERE dataset='2_27' AND position='MID' AND minutes>=900
ORDER BY progressive_passes_per90 DESC LIMIT 20;

-- 3. Current player totals with the denominator for each supplied field.
SELECT league,player_id,player,COUNT(*) AS recorded_appearances,
       SUM(json_extract(stats_json,'$.totalGoals')) AS goals,
       COUNT(json_extract(stats_json,'$.totalGoals')) AS matches_with_goal_field
FROM player_appearances
WHERE json_extract(stats_json,'$.appearances')>0
GROUP BY league,player_id,player ORDER BY goals DESC LIMIT 20;

-- 4. Provider shot xG versus finishing. Not causal evidence of finishing skill.
SELECT player_id,COUNT(*) AS non_penalty_shots,ROUND(SUM(xg),2) AS npxg,
       SUM(goal) AS goals,ROUND(SUM(goal)-SUM(xg),2) AS goals_minus_xg
FROM shots WHERE penalty=0 GROUP BY player_id HAVING COUNT(*)>=50
ORDER BY goals_minus_xg DESC LIMIT 20;
