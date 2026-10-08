# USDJPY Version B, RR 9, BE 3R, SL = 1 × box: relative small-box filter

Protocol fixed before any result: skip the day if its box < k × median box of the previous 20 tradable days; k = none, 0.3, 0.5, 0.7. All numbers after $7/lot, swap (+1% markup) and 0.2 pip slippage per stop fill. Pick on 2010–2017 by avg R; check on 2018–2026.

**Pick: box < 0.3 × median.** Check 2018–2026: avg R +0.156 (t +2.48), +344% at 0.5% risk, max DD 29%.

| Period · filter | days traded | trades | win rate % | avg R | t | losing streak | max DD % (1%) | max DD % (0.5%) | return % (0.5%) | per year % (0.5%) |
|---|---|---|---|---|---|---|---|---|---|---|
| design 2010–2017 · none | 1971.000 | 2233.000 | 23.556 | 0.061 | 1.005 | 35.000 | 67.182 | 39.264 | 57.664 | 5.862 |
| check 2018–2026 · none | 2059.000 | 2323.000 | 22.858 | 0.154 | 2.452 | 24.000 | 50.270 | 29.029 | 333.337 | 18.219 |
| design 2010–2017 · box < 0.3 × median | 1964.000 | 2223.000 | 23.662 | 0.066 | 1.079 | 35.000 | 66.552 | 39.190 | 64.215 | 6.403 |
| check 2018–2026 · box < 0.3 × median | 2054.000 | 2317.000 | 22.918 | 0.156 | 2.481 | 24.000 | 50.257 | 28.973 | 343.979 | 18.547 |
| design 2010–2017 · box < 0.5 × median | 1859.000 | 2096.000 | 23.998 | 0.051 | 0.816 | 34.000 | 60.165 | 34.359 | 37.958 | 4.109 |
| check 2018–2026 · box < 0.5 × median | 1965.000 | 2216.000 | 23.060 | 0.148 | 2.305 | 26.000 | 55.088 | 31.827 | 279.316 | 16.436 |
| design 2010–2017 · box < 0.7 × median | 1547.000 | 1739.000 | 23.807 | 0.015 | 0.228 | 29.000 | 70.227 | 43.106 | -3.152 | -0.400 |
| check 2018–2026 · box < 0.7 × median | 1659.000 | 1856.000 | 22.629 | 0.150 | 2.143 | 23.000 | 43.996 | 24.013 | 213.220 | 13.919 |
