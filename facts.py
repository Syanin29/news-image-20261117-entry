#!/usr/bin/env python3
"""Verified facts for Tuesday 17 November 2026 — the ONLY facts the
renderer may print. Every story was cross-checked against at least
two independent sources (Reuters / AP / BBC / CNN / Bloomberg and
their syndication) and confirmed as happening, or first reported,
on 17 November 2026. One disputed item (an unreviewed claim about
Jeffrey Epstein's death) was deliberately left out.

Fields per story: region tag, headline (<=6 words), one-line deck,
big stat. Story 1 is the hero. Figures are as reported; where two
sources disagreed on a toll, the lower official figure is used.
"""

DATE_LINE = "TUESDAY, 17 NOVEMBER 2026"
MASTHEAD = "WORLD NEWS"
SUBHEAD = "24 STORIES  •  6 CONTINENTS  •  ONE DAY"

HERO = {
    "tag": "UKRAINE WAR",
    "headline": "KERCH BRIDGE SPAN DESTROYED",
    "deck": ("Ukraine's drones and missiles drop the road arch into the "
             "Kerch Strait; rail back on one track, road shut."),
    "stat": "19 KM  •  2 KILLED",
}

# Ordered by importance. tag = region/beat, stat = the number that sticks.
STORIES = [
    {"tag": "TECH", "headline": "NVIDIA SALES DOUBLE WITHOUT HUANG",
     "deck": "First results since Huang quit: $115.8B revenue, +103%; Q4 guide $130B.",
     "stat": "$115.8B  +103%"},
    {"tag": "HEALTH", "headline": "US LOSES MEASLES-FREE STATUS",
     "deck": "PAHO ends 26 years of elimination; 5,412 cases in 2026, most in 35 years.",
     "stat": "5,412 CASES"},
    {"tag": "ASIA", "headline": "TRUMP LANDS IN MANILA",
     "deck": "ASEAN-US summit opens; Thailand to buy $2.6B of US farm goods.",
     "stat": "$2.6B DEAL"},
    {"tag": "GULF", "headline": "IRAN HITS US RADAR IN BAHRAIN",
     "deck": "Third drone strike on US targets in days; no casualties reported.",
     "stat": "3RD STRIKE"},
    {"tag": "ENERGY", "headline": "4 TANKERS HIT BY MINES",
     "deck": "Tankers burn in the Strait of Hormuz; Brent crude at $92.76 a barrel.",
     "stat": "BRENT $92.76"},
    {"tag": "EUROPE", "headline": "RUSSIAN MILITARY PLANE CRASHES",
     "deck": "An-12 transport down in Siberia; all aboard killed, ministry says.",
     "stat": "19 KILLED"},
    {"tag": "ASIA", "headline": "RUSSIAN JETS ENTER JAPAN AIRSPACE",
     "deck": "Two aircraft cross in ~3 minutes each; Tokyo lodges sternest protest.",
     "stat": "1ST SINCE SEP 2024"},
    {"tag": "MIDEAST", "headline": "KNESSET OUSTS NETANYAHU ALLY",
     "deck": "Matan Kahana elected speaker 66-52, replacing Ofir Katz.",
     "stat": "66-52 VOTE"},
    {"tag": "EUROPE", "headline": "UK SANCTIONS SETTLEMENT BUILDERS",
     "deck": "Eight West Bank firms hit, plus activists blocking Gaza aid.",
     "stat": "8 FIRMS"},
    {"tag": "MIDEAST", "headline": "SETTLER SHOOTS WOMAN, 72, DEAD",
     "deck": "Palestinian woman killed in Jericho; 10 wounded in settler attack.",
     "stat": "1 KILLED, 10 HURT"},
    {"tag": "MIDEAST", "headline": "HOUTHIS ADVANCE ON BAB AL-MANDEB",
     "deck": "Yemeni forces pull back from the Red Sea coast to defend Aden.",
     "stat": "KEY TRADE STRAIT"},
    {"tag": "AFRICA", "headline": "17 KILLED IN TWO MASS SHOOTINGS",
     "deck": "Nine dead near Pretoria, eight in Johannesburg; police hunt the gunmen.",
     "stat": "17 DEAD"},
    {"tag": "AMERICAS", "headline": "JPMORGAN GLITCH HITS BANKING",
     "deck": "Software bug slows online banking and Zelle; FBI rules out cyberattack.",
     "stat": "~5,000 REPORTS"},
    {"tag": "AMERICAS", "headline": "PENTAGON FAILS 9TH AUDIT IN A ROW",
     "deck": "Just 14 of 25 entities pass; $4.8T in assets unaccounted for.",
     "stat": "$4.8T ASSETS"},
    {"tag": "EUROPE", "headline": "EU CHARGES TEMU OVER ILLEGAL GOODS",
     "deck": "Brussels: marketplace failed to stop unsafe sales; fines up to 6%.",
     "stat": "UP TO 6% FINE"},
    {"tag": "ASIA", "headline": "MONGOLIA PRESIDENT TO RESIGN",
     "deck": "Khurelsukh quits over $25M bribery claim tied to a $1.28B rail project.",
     "stat": "$25M CLAIM"},
    {"tag": "EUROPE", "headline": "FRANCE STRIKES OVER PAY",
     "deck": "Public workers march across France; unions claim 500,000 on streets.",
     "stat": "146,000 MARCH"},
    {"tag": "AMERICAS", "headline": "POPE LEO ENDS SOUTH AMERICA TOUR",
     "deck": "Twelve days, 50 events and 13 million people; 3 million in Lima alone.",
     "stat": "13M PEOPLE"},
    {"tag": "EUROPE", "headline": "DEPARDIEU DROPS APPEAL, GUILTY",
     "deck": "Actor accepts conviction; 18-month suspended term, 29,040 euro fine.",
     "stat": "18 MONTHS SUSPENDED"},
    {"tag": "SPACE", "headline": "VULCAN ROCKET FAILS, 40 SATELLITES LOST",
     "deck": "ULA's first total failure since 2006 dooms Amazon's Leo satellites.",
     "stat": "40 SATELLITES"},
    {"tag": "GLOBAL", "headline": "128 NATIONS DEBATE KILLER ROBOTS",
     "deck": "Geneva talks on killer robots; US, Russia, Israel resist binding rules.",
     "stat": "128 NATIONS"},
    {"tag": "CULTURE", "headline": "PATTINSON IS THE NEW JAMES BOND",
     "deck": "Seventh 007 named for the 26th film; Denis Villeneuve to direct.",
     "stat": "7TH BOND"},
    {"tag": "SPORT", "headline": "SANTNER OUT OF INDIA TESTS",
     "deck": "New Zealand captain fractures his right hand; Foxcroft called up.",
     "stat": "2 TESTS MISSED"},
]

# Four numbers for the big-stat strip (must match stories above).
BIG_STATS = [
    ("$115.8B", "NVIDIA REVENUE, +103%"),
    ("5,412", "US MEASLES CASES IN 2026"),
    ("19 KM", "KERCH BRIDGE SPAN DOWN"),
    ("4", "TANKERS HIT IN HORMUZ"),
]

FOOTER_SOURCES = ("SOURCES: REUTERS  •  AP  •  BBC  •  CNN  •  BLOOMBERG  •  PAHO  •  CDC  •  "
                   "ALL STORIES VERIFIED 17 NOV 2026  •  PHOTOS: AI-GENERATED ILLUSTRATIONS")
