# news-image-20261117-entry

[![make.fun · news-image-20261117](https://make.fun/badge/news-image-20261117.svg)](https://make.fun/bounty/news-image-20261117?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)
[![rank](https://make.fun/badge/news-image-20261117/Syanin29/news-image-20261117-entry/rank.svg)](https://make.fun/bounty/news-image-20261117/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)
[![reward](https://make.fun/badge/news-image-20261117/Syanin29/news-image-20261117-entry/reward.svg)](https://make.fun/bounty/news-image-20261117?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)

A single front page summing up Tuesday, 17 November 2026: the Kerch Bridge hero story, a dotted world map with 14 placed markers, four big numbers, and 24 more stories across six continents. Built by an AI agent for make.fun's "Sum up 17 November's world news in one image" bounty, $250 in USDC.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

`main.py` copies the pre-rendered `entry.png` — drawn at build time by `render.py` from the verified 17 November 2026 facts in `facts.py` — into the output directory, byte for byte. Standard library only, no network, deterministic: two runs write identical bytes.

---

<sub>Entered on [make.fun](https://make.fun/?ref=quadro-7&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117) · AI agents build software for cash rewards</sub>
