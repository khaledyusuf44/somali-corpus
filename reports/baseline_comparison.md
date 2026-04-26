# Baseline corpora — Somali (Phase 0.4 report)

Generated 2026-04-23 from downloaded sources.

## Per-corpus stats
| Source | Docs | File MB | Whitespace words | Approx tokens | Unique hashes (within-corpus) |
|---|---:|---:|---:|---:|---:|
| wikipedia-so | 9,021 | 13.79 | 1,903,892 | 2,475,059 | 9,007 (drops 14) |
| cc100-so | 396,524 | 412.09 | 62,331,139 | 81,030,480 | 374,740 (drops 21,784) |
| hplt2-so | 966,507 | 2592.91 | 388,756,093 | 505,382,920 | 799,619 (drops 166,888) |

## Length distribution (word count buckets)
| Source | <50w | 50-199w | 200-999w | 1k-5kw | >=5kw |
|---|---:|---:|---:|---:|---:|
| wikipedia-so | 3,330 | 3,470 | 1,919 | 283 | 19 |
| cc100-so | 113,581 | 197,841 | 80,880 | 4,100 | 122 |
| hplt2-so | 15 | 410,560 | 493,080 | 60,199 | 2,653 |

## Cross-corpus exact-dedup overlap
After normalize (lowercase + whitespace-collapse) and SHA-256 truncated hash:

- **wikipedia-so ∩ cc100-so**: 11 shared docs (0.12% of wikipedia-so, 0.00% of cc100-so)
- **wikipedia-so ∩ hplt2-so**: 2 shared docs (0.02% of wikipedia-so, 0.00% of hplt2-so)
- **cc100-so ∩ hplt2-so**: 993 shared docs (0.26% of cc100-so, 0.12% of hplt2-so)
- **total unique across all corpora**: 1,182,360 docs

## Sample docs (manual quality check)

### wikipedia-so

**sample 1** (id `wiki_so_32308`, 10 words)

> daalib waa tijaabka yoolka qofka, ee ingiriis loo yaqaano motivation.

**sample 2** (id `wiki_so_33518`, 106 words)

> Eungyo (), sidoo kale loogu yeero A Muse waddamada qaarkood, waa la- filimka erotic-ka ee Koonfur Kuuriya ee 2012 ee qoraaga Park Bum-shin Eun-gyo. Abwaan 70 jir ah ayaa jaceyl u qaaday gabar dugsiga sare ah waxaana lagu dhiiri galiyay inuu sheeko gaaban ka qoro iyada, laakiin ardaygiisii ​​oo ka ma…

**sample 3** (id `wiki_so_4124`, 19 words)

> Riyaalu Saalixiin waa kitaab uu qoray Imaam Nawawi kaas oo ka kooban 1896 Xadiis oo u qeysama 372 Qeybood,

### cc100-so

**sample 1** (id `cc100-so_201979`, 118 words)

> Somalia, November 24, 2015 (Daljir) â€” Dowladda Mareykanka ayaa sheegay inay kusoo rogayso xayiraado Afar ka mid ah Masâ€™uuliyiinta Burundi, kuwaasoo ay ku jiraan Xubno horay xilal uga soo qabtay xukuumadda; waxaana dhamaan lala xiriiriyay Qalalaasaha ka taagan dalkaas. Afarta masâ€™uul ee laga xa…

**sample 2** (id `cc100-so_220500`, 132 words)

> Aadanuhu waa mid ogsoon mar walba in ay jirto awood isaga ka weyn oo abuurtay, intooda badani waa kuwo diin leh oo kutubta samaawigaa rumaysan, xagga qaarkood ka leexato oo meel iyagu samaysta waxa ay caabudayaan, waana dhaqan soo jireen ah maantana waddamada Hindiya iyo Jaynuhu tusaale kuugu filan …

**sample 3** (id `cc100-so_21225`, 30 words)

> Waxaa si guud looga wadda dooday sida la isaga kaashan karo wadda shaqeynta ka dhaxeysa maamulada degmooyinka iyo hay’adaha Amniga. Maxaa Eritereya cunaqabateynta looga qaaday oo Soomaaliya looga qaadi waayey?

### hplt2-so

**sample 1** (id `hplt2-so_885440`, 224 words)

> XOG: C/wali Gaas oo diiday dalab kaga yimid QM oo ku aadan Xiisada Tukaraq(Go’aan Cajiib uu gaaray) Sida ay illo xog ogaal ah inoo sheegeen,madaxweynaha Maamulka Puntland Dr. C/wali Maxamed Cali Gaas ayaa diiday baaq kaga yimid Qaramada Midoobay oo ku aadan in wada hadal iyo waan waan lagu dhammeeyo…

**sample 2** (id `hplt2-so_403958`, 109 words)

> Dhamaan Dadka Muslimiinta Waxaan Leenahay Ciid Mubaarak. Iyadoo maanta ay tahay Kowda bisha Shawaal maalin Axad ah waa maalinta kowaad ee Ciidul Fidri waxa uu Webseydka Calamada dhageytayaashiisa iyo akhristayaashiisa iyo guud ahaan Muslimiinta caalamka ugu hambalyeynayaa munaasabada Ciidul Fidriga …

**sample 3** (id `hplt2-so_794772`, 165 words)

> Sida ay sheegayaan warbixino ka imaanaya gudaha dalka talyaaniga – Maamulka Milan ayaa kulan la yeelanaya maanta madaxweynaha Torino Urbano Cairo si ay uga wadahadlaan arinta ku saabsan Andrea Belotti. Weeraryahankaan heerka caalami ayaa dhaliyay 26-gool xilli ciyaareedkii dhamaaday ee Serie A-da, s…

## Implications

- **HPLT v2 dwarfs every other source** — at ~505M approx tokens it is already 5× our original corpus target. The project math shifts: the question is no longer "can we find 100M tokens of Somali" but "what's the right dedup + quality filter applied to HPLT that beats HPLT-raw on downstream metrics."
- **CC100 is cleaner than I expected** (~81M tokens, 396k docs) but has a long tail of under-50-word docs (28% of its documents); HPLT's cleaning already drops that tail almost entirely (15 docs of 966k).
- **Wikipedia-so is not a corpus contributor** — 2.5M tokens is 0.5% of HPLT — but it remains the cleanest Somali text we have, ideal as positive-class seed for the Phase 6 perplexity quality filter.
- **Cross-corpus overlap numbers below** answer whether merging HPLT + CC100 adds meaningful docs or just repeats. This is the first concrete data point on how much value aggregation gives us.
