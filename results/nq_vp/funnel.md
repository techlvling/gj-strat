### Where the 1m setups end (full period)

Every setup that started (a sweep of the obvious level inside the window) ends in one of: a signal, death for no drive-in at the final sweep extreme, death for no drive-out within 5 bars, or still open at 11:00.

| index | base 0930|POC|B2on|BEoff | no-filter 2R BEoff |
|---|---|---|
| signal | 16 | 179 |
| died_no_drive_in | 872 | 1,539 |
|   drive-in: no gap, has big body | 7 | 92 |
|   drive-in: gap, no big body | 771 | 1,259 |
|   drive-in: neither | 94 | 188 |
| died_no_drive_out | 248 | 718 |
|   drive-out: a big bar, none closed above gap | 1 | 27 |
|   drive-out: closed above gap, body too small | 138 | 386 |
|   drive-out: big bar and reclaim on different bars | 1 | 13 |
|   drive-out: neither | 108 | 292 |
| died_window_end | 259 | 236 |

base 0930|POC|B2on|BEoff, setups that died with drive-in OK: median distance from sweep extreme to gap top = 0.88 x ATR(14, 15m); median best drive-out body in the 5 bars = 0.84 x ATR(20, 1m) (needs 1.5).

no-filter 2R BEoff, setups that died with drive-in OK: median distance from sweep extreme to gap top = 1.21 x ATR(14, 15m); median best drive-out body in the 5 bars = 0.91 x ATR(20, 1m) (needs 1.5).

Interpretation check (not a variant, not ranked): if ATR(20, 1m) for the body tests used the 20 bars BEFORE the tested bar instead of including it, total trades over the full period would be:

| combo | trades, full period |
|---|---|
| 0930|POC|B2on|BEoff | 12 |
| 0930|POC|B2on|BEon | 12 |
| 0930|POC|B2off|BEoff | 8 |
| 0930|POC|B2off|BEon | 8 |
| 0930|2R|B2on|BEoff | 17 |
| 0930|2R|B2on|BEon | 17 |
| 0930|2R|B2off|BEoff | 13 |
| 0930|2R|B2off|BEon | 13 |
| 0945|POC|B2on|BEoff | 6 |
| 0945|POC|B2on|BEon | 6 |
| 0945|POC|B2off|BEoff | 2 |
| 0945|POC|B2off|BEon | 2 |
| 0945|2R|B2on|BEoff | 9 |
| 0945|2R|B2on|BEon | 9 |
| 0945|2R|B2off|BEoff | 5 |
| 0945|2R|B2off|BEon | 5 |
| NOFILTER|2R|BEoff | 115 |
| NOFILTER|2R|BEon | 115 |

Base rate: 4.4% of all 1m bars 09:30-11:00 have a body >= 1.5 x ATR(20, 1m) (either direction).
