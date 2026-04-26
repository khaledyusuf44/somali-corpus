# Phase 5 — Quality filter (char-5-gram coverage)

- Seed: Wikipedia-so articles ≥ 200 words — 2,221 docs, ~1,464,023 tokens, 828,294 unique 5-grams
- Scoring elapsed: 316.0s for 963,908 docs
- Threshold (drop bottom 15%): score=0.9029
- Input docs: 963,908
- Output docs: 819,322
- Dropped: 144,586 (15.00%)

## Per-source kept
| Source | Input | Kept | Drop rate |
|---|---:|---:|---:|
| wikipedia-so | 4,624 | 3,671 | 20.61% |
| cc100-so | 247,672 | 233,394 | 5.76% |
| hplt2-so | 711,612 | 582,257 | 18.18% |

## Samples by score decile

### Decile 1 (score range ~0.062–0.885) — `DROP`

**hplt2-so** score=0.859 n_words=264

> Najma Nashaad iyo Sharma Boy HEESTA HUBQAAD - FANAAN WASIIR MR HUBQAAD MOHAMED XAYIR MAAREEYE Khadar Keyow hees cusub RAXMA - Qiso Jaceyl dhaba Fadumiina Hilowle hees dadkaan adi kuu jeclahay Fadumiina Hilowle hees cusub SAAN LEE RABBAA Dayax dalnuurshe hees Lama iloowaan Hees Ii…

**hplt2-so** score=0.8549 n_words=273

> ☑ Gaadiidka Caalamiga ah ee bilaashka ah. ☑ Lacag Canshuur ah Lama Yaabo. ☑ Dammaanadda Saacadaha Ugu Fiican. Lacag celin hadii aadan helin amarkaaga. Soo celinta & Hayso sheyga, haddii uusan ahayn sidii lagu tilmaamay. - Da ': 10-45 sano - Magaca Waaxda: Haweenka - Nambarka Tusa…

**hplt2-so** score=0.73 n_words=172

> Sawirro Heegan Buuxa Oo La Galiyay Ciidanka Xasilinta Ka Dib Qaraxii Xalay Ka Dhacay Magaalada Muqdisho feejignaan dheeri ah ayay muujinayaan ciidamada xasilinta amniga Muqdisho kadib weerarkii ku bilaawday qaraxyada ee lagu qaaday Maqaayadda Pizza House kaas oo dad badani ay ku …

### Decile 2 (score range ~0.885–0.915) — `keep`

**cc100-so** score=0.9083 n_words=115

> Wacdi iyo Waano. DEG-DEG AH:Muusse Biixi Oo Ku Dhawaaqay Golaha Wasiirada Xukumaddiisa. Yuusuf Garaad Oo Booqday Maxaabiista Soomaaliyeed Ee Ku xidhan Dalka Seychelles. Si kastaba ha ahaatee,Israa'iil;maanta waa dal awood badan oo ay aqoonsanyihiin inka badan 160 wadan,halka dadk…

**hplt2-so** score=0.8983 n_words=369

> Qofkii ugu Da'da yaraa iyo kii ugu Da'da weynaa ee ka qayb galay Ciyaaraha *Olymbic Games-ka* oo kala Noqday. Zeinab Mohamed Khaireh iyo ... Dadka ka qaybqaadanaaya Ciyaaraha Caalamiga ah *Olymbic Games* ee ka socda dalka Greece ayaa waxa ugu Da'a yaraatay Gabadh yar oo layidhaah…

**hplt2-so** score=0.9074 n_words=242

> Lakulan: 74-jir ku labista dharka gabdhaha si uu hooyadiisa gabar la'aanta ah uga farxiyo. Posted by: Zakariya in Wararka March 13, 2017 279 Views 2017-03-13 Beijing (Himilonews) – Toddobaad kasta 14-kii sano ee lasoo dhaafay, Li Yinglai, oo ah waayeel ku nool Kunming ee China, w…

### Decile 3 (score range ~0.915–0.932) — `keep`

**cc100-so** score=0.9258 n_words=358

> Dagaalada u dhaxeeya cwxo iyo kuwa gumaysiga itoobiya ayaa dhex maray cwxo iyo kuwa gumaysiga Itoobiya ayaa ciidanka cadowga itoobiya lagaga dilay 4 askari waxaana lagaga la hubo 12 wayaane iyo 15 kale oo la dhaawacay waxaana 14/03/09 Gorayga oo ka tirsan Dhagaxmadow dagaal ka 13…

**hplt2-so** score=0.9235 n_words=950

> 1Markaasuu Samsoon tegey Gaasa, oo halkaas wuxuu ku arkay dhillo, wuuna u galay. 2Oo waxaa dadkii reer Gaasa lagu yidhi, Samsoon halkanuu yimid. Oo intay hareereeyeen ayay habeenkii oo dhan magaalada iriddeeda ku gaadayeen, oo habeenkaas oo dhanna way aamusnaayeen, oo waxay yidha…

**hplt2-so** score=0.9273 n_words=487

> Galaydh dhugo dhankaagaa tolkaa, looga soo dhacaye! Waa laba aan is qabanayn, sida shacabka dhulbahante wax u doonayaan iyo damaca gaarka ah ee G6, runtii waa wax kala fog daacadnimada shacabka SSC iyo booraan u qodka shirka khaatumo ee G6. Aan soo dhawaado oo idhaahdo. Ina ciise…

### Decile 4 (score range ~0.932–0.944) — `keep`

**hplt2-so** score=0.9385 n_words=144

> Ninkani oo baraha bulshada looga yaqaan "ibliiska sacuudiga" ayaa markale muuqaal ka soo muuqday, laakin markani waxa uu la soo baxay gar dheer oo aan looga baran iyo make up l'aan. XAQIIQONEWS-Wararka Dibadda Ninkani ayaa sidii caadadiisa aheyd waxa uu daafacay Ibliis waxa uuna …

**hplt2-so** score=0.9419 n_words=134

> Kooxda Manchester United oo dhagaysanaysa dalabyada u imaanaya Romelu Lukaku (Manchester) 20 Abriil 2019. Kooxda kubadda cagta Manchester United ayaa la soo warinayaa inay dhagaysan doonto dalabyada u imaanaya ciyaaryahankeeda Lukaku, kaasoo ay xiisanayaan kooxo dhowr ah. Jariira…

**hplt2-so** score=0.9362 n_words=1269

> Qoraallo La Xiriira Qoraallo Hore... Magaalada Madiina iyo agagaarkeeda ayaa waxaa ka dhacday abaar aad iyo aad u daran oo dhibaato xun gaadhsiisay dadkii iyo duunyadiiba. Wixii waro ahaa iyo ceelashiiba way gudheen. Waxay dadku aad u sugayeen roob, wuuse di'i la'yahay wayna dhee…

### Decile 5 (score range ~0.944–0.953) — `keep`

**hplt2-so** score=0.9503 n_words=243

> Ma Dhabbaa In Siyaasi Mukhtaar Jibriil Loo Magacaabayo Kaambaynarka Xisbiga Kulmiye September 12, 2017 - Written by gabiley office Gabiley(GNO)-Iyada oo ay kaabiga soo saaran tahay Doorashadii Madaxtooyada oo ay ka hadhsan tahay mudo Laba Bilood iyo dhawr, isla markaana Ay bilaab…

**hplt2-so** score=0.9476 n_words=186

> Daawo:Xaragada Daa'uuska iyo Quruxda Rabi ku manaystay. Published on December 31, 2014 by xalane xudur · No Comments Daa'uusku waa Nooc kamid ah Xayawaanka Dunida kuyar waxaana lagu sheegaa inuu Yahay noolaha ugu Quruxda badan ee Dunida Rabi keenay, laakiin waxaa uu leeyahay Boog…

**hplt2-so** score=0.9458 n_words=102

> Faahin faahin dheeraad ah ayaa ka soo baxaysa qarax caawa fiidkii ka dhacay magaalada Muqdisho, kaasi oo loo adeegsaday gaari laga soo buuxiyay waxyaabaha qarxa oo la dhigay agagaarka Isbitaalka Daaru_shifa ee magaalada Muqdisho. Qaraxa ayaa inta la ogyahay waxaa ku geeriyooday l…

### Decile 6 (score range ~0.953–0.960) — `keep`

**cc100-so** score=0.9544 n_words=182

> Cod iyo Muqaal: Gaalkacyo, Soomaaliya: Isbitaalka iyo Xarumaha Caafimaadka MSF ee lacag la'aanta ah - Waa Nolosha Dadweynaha' - MSF Gudaha Soomaaliya- Helitaanka daryeel Caafimaad Cod iyo Muqaal: Gaalkacyo, Soomaaliya: Isbitaalka iyo Xarumaha Caafimaadka MSF ee lacag la'aanta ah …

**hplt2-so** score=0.9539 n_words=283

> DHAGEYSO COD:— UN IYO Nicholas Kay oo wax ka bedalay mawqifkoodii, sheegayna in heshiiskii Muqdisho uu yahay Gal-Mudug iyo Galgaduud Ergeyga gaarka ah ee Qaramada Midoobay u qaabilsan Soomaaliya Nicholas Kay oo waraysi siiyey Idaacadda VOA-da, ayaa sheegay in heshiiskii dhowaan m…

**hplt2-so** score=0.9592 n_words=198

> Tinta waxaa jecel rag iyo haween, inta badan raga waa u dul-qaataan bidaarta iyo wixii la mid ah halka Haweenka ay geeri ka xigaan. Dooda tinta ku saabsan guri walba wey ka jirtaa, inta badan waxaa lagu kaftamaa qofka ay timaha ka xanaaqaan ama ka jarmaan. Tinta oo go'da, Dadka q…

### Decile 7 (score range ~0.960–0.967) — `keep`

**cc100-so** score=0.9668 n_words=112

> Addis-Ababa -Wararka naga soo gaaraya Magaalada Addis Ababa ee xarunta dalka Itoobiya ayaa waxa ay sheegayaan in maanta halkaasi si weyn loogu soo dhaweeyay Hoggaamiyaha Ururka ONLF iyo Wafdi uu hoggaaminayo. Wafdigan oo ka kooban 20 Xubnood,waxaa uu qorshuhu ahaa in Arbacadii la…

**cc100-so** score=0.9652 n_words=93

> Kuwani waa bogag dibedda ah, waxayna ku furmayaan bog cusub Dagaalyahanada kooxda Boko Xaram, ayaa waxa ay weeerar ku qaadeen degmada Mainok, maalin cad oo dadku ay suuqa ka buuxaan. Qof degmadaasi ku nool ayaa BBCda u sheegay, in qaar ka mid ah dad naftooda u cararayay ay dhinte…

**hplt2-so** score=0.9627 n_words=279

> Wasiirka Beeraha Oo Dalka Ku Soo Laabtay Kana Warbixiyey Hawlo Shaqo Oo Uu Ku Maqnaa June 1, 2015 - Written by Mustafe Faro Hargeysa (Hubaal) Wasiirka Wasaaradda Beeraha Somaliland Maxamed Aw Daahir Ibraahim oo safar shaqo ugu maqnaa dalka dibadiisa ayaa maanta dalka ku soo laabt…

### Decile 8 (score range ~0.967–0.974) — `keep`

**cc100-so** score=0.9699 n_words=89

> Xoogagga weerarka soo qaaday ayaa la sheegay in ay beegsadeen saldhig ciidan oo ku yaala aagga halka lagu magacaabo Buulo-Fooliyo, waxaana la tuhusan yahay in dagaalamayaasha weerarka soo qaaday ka soo kicitimeen dhinaca degmada Awdheegle. Ilaa iyo hadda dhab ahaan lama oga khasa…

**hplt2-so** score=0.9726 n_words=106

> Wasiirka Ayaa ugu horeyn waxuu warbaxin ka siiyay wasiirka arrimaha diiwaanka Horumarka dowladda Soomaaliya ay sameysay iyo cilaaqaadka soo jireenka ah ee ka dhaxeeyo Dowladdaha Soomaaliya iyo Kuwait. Mudane jamaal Maxmaed Xasan ayaa dowlada kuwait ujeediyay in mahsaariicda horum…

**hplt2-so** score=0.9684 n_words=278

> Wafdi uu hoggaaminayo Guddoomiye ku xigeen arrimaha horumarinta gobollada Xiriirka Soomaaliyeed ee Kubadda cagta oo maanta gaaray Magaalada Jowhar (Jowhar) 25 Maajo 2019. Wafdi uu hoggaaminayo Guddoomiye ku xigeen arrimaha horumarinta gobollada Xiriirka Soomaaliyeed ee Kubadda ca…

### Decile 9 (score range ~0.974–0.982) — `keep`

**cc100-so** score=0.9748 n_words=207

> Xoghayaha Arimaha Dibada Maraykanka ayaa markiiba hadalka ku bilaabay in Dowlada Maraykanku ay sii wadayaan wada shaqaynta Maraykanka kala dhaxeysay Soomaaliya, wuxuuna xoghayaha arrimaha dibadda ee maraykanka John Kerry sheegay inay qaranimada soomaliyeed ay wax badan ka dhiman …

**cc100-so** score=0.9745 n_words=78

> Madaxweyne Farmaajo ayaa warbixinno ka dhegaysan doona mas'uuliyiinta goobaha uu booqan doono,waxaana la filayaa in uu hadal ka jeediyo xarumaha uu soo kormeerayo,inkastoo aan la ogayn qodobada uu si gaar ah uga hadli doono. Qaban qaabo ku aadan soo dhoweynta wefdiga Madaxweynaha…

**cc100-so** score=0.9816 n_words=226

> Soomaalida ayaa tidha Ninka Aan Garan Waxa Taagan, Waxa Soo Socda , taasoo macnaheedu noqon karo in Somaliland gasho marxalad ka duwan tii nabadda iyo barwaaqada lahayd ee ay kusoo noolaayeen 18 sano oo dalkani xor ahaa. Waxa maanta ugu daran laba arrimood oo midkood yahay dhaawa…

### Decile 10 (score range ~0.982–1.000) — `keep`

**cc100-so** score=0.9956 n_words=82

> Waxaa Xaalad deganaansho ah laga dareemayaa degmada Qoryooleey ee Gobolka Shabeellaha hoose oo xalay ay ku dagaalameen maleeshiyada Alshabaab iyo ciidamada maamulka degmada oo taageero ka helaayo ciidamada AMISOM. Dagaalka oo mudo saacado ah socday ayaa ugu dambeyn waxaa la jebiy…

**cc100-so** score=0.9863 n_words=94

> Magaalada Kismaayo ee xarunta KMG ee maamulka Jubbaland waxaa laga dhisay xarun loogu tala galay in lagu dhaqan celiyo waxna lagu baro maleeshiyaadka hubeysan iyo sidoo kaled dhalinyarada marin habowday taasi oo dhismaheeda ay gacan ka geysatay dowladda Jarmalka. Dhismaha xarunta…

**hplt2-so** score=0.9889 n_words=119

> Diyaarado dagaal oo dulmaraya Magaalooyinka Jubbada hoose Deegaanada Al Shabaab ay kusugan yihiin gobolka Jubbada Hoose ayaa lasoo sheegayaa in ay xalay ilaa Saaka aroortii diyaarado joog hoose kusocday ay dul heehaabayeen halkaasi. Wararka waxay sheegayaan in Diyaaradahaan ay yi…
