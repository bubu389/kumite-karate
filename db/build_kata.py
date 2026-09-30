"""Load the WKF Kata + Para Karate rules and the Kata exam question bank into kumite_kb.sqlite.

Run from the repo root:  python3 db/build_kata.py
Needs `pdftotext` (poppler-utils). Rebuilds only the kata_* tables; the Kumite tables are untouched.
"""
import json
import re
import sqlite3
import subprocess

DB = "db/kumite_kb.sqlite"
KATA_RULES_PDF = "WKF_Kata_Rules 2026 (1).pdf"
PARA_RULES_PDF = "WKF_Para_Karate_Kata_Rules_2026.pdf"
QUESTIONS_PDF = "Kata_ParaKarate questions_EnglishDec2025.pdf"

KATA_LIST = [
    "Anan", "Anan Dai", "Ananko", "Aoyagi", "Bassai", "Bassai Dai", "Bassai Sho", "Chatanyara Kusanku",
    "Chibana No Kushanku", "Chinte", "Chinto", "Enpi", "Fukyugata Ichi", "Fukyugata Ni", "Gankaku", "Garyu",
    "Gekisai (Geksai) 1", "Gekisai (Geksai) 2", "Gojushiho", "Gojushiho Dai", "Gojushiho Sho", "Hakusho",
    "Hangetsu", "Haufa (Haffa)", "Heian Shodan", "Heian Nidan", "Heian Sandan", "Heian Yondan", "Heian Godan",
    "Heiku", "Ishimine Bassai", "Itosu Rohai Shodan", "Itosu Rohai Nidan", "Itosu Rohai Sandan", "Jiin", "Jion",
    "Jitte", "Juroku", "Kanchin", "Kanku Dai", "Kanku Sho", "Kanshu", "Kishimono No Kushanku", "Kousoukun",
    "Kousoukun Dai", "Kousoukun Sho", "Kururunfa", "Kusanku", "Kyan No Chinto", "Kyan No Wanshu", "Matsukaze",
    "Matsumura Bassai", "Matsumura Rohai", "Meikyo", "Myojo", "Naifanchin Shodan", "Naifanchin Nidan",
    "Naifanchin Sandan", "Naihanchi", "Nijushiho", "Nipaipo", "Niseishi", "Ohan", "Ohan Dai",
    "Oyadomari No Passai", "Pachu", "Paiku", "Papuren", "Passai", "Pinan Shodan", "Pinan Nidan", "Pinan Sandan",
    "Pinan Yondan", "Pinan Godan", "Rohai", "Saifa", "Sanchin", "Sansai", "Sanseiru", "Sanseru", "Seichin",
    "Seienchin (Seiyunchin)", "Seipai", "Seiryu", "Seishan", "Seisan (Sesan)", "Shiho Kousoukun", "Shinpa",
    "Shinsei", "Shisochin", "Sochin", "Suparinpei", "Tekki Shodan", "Tekki Nidan", "Tekki Sandan", "Tensho",
    "Tomari Bassai", "Unshu", "Unsu", "Useishi", "Wankan", "Wanshu",
]
assert len(KATA_LIST) == 102
KATA_LIST_TEXT = ("Official WKF Kata list (102 kata): "
                  + "; ".join(f"{i} {k}" for i, k in enumerate(KATA_LIST, 1))
                  + ". In reporting the kata to be performed use the designated number. Should there be "
                    "inconsistency between the number and the name of the kata, the number will be considered "
                    "the reported kata to be performed.")

ARTICLE_TITLES = {
    "KATA": {
        "1": "KATA COMPETITION AREA", "2": "OFFICIAL ATTIRE", "3": "ORGANISATION OF KATA COMPETITION",
        "4": "THE JUDGING PANEL", "5": "EVALUATION", "6": "OPERATION OF MATCHES", "7": "OFFICIAL PROTEST",
        "8": "ELIGIBILITY TO COMPETE",
        "9": "ADAPTATION OF THESE RULES TO EVENTS OUTSIDE THE WKF OFFICIAL EVENT PROGRAMME",
        "10": "ISSUES NOT SPECIFICALLY COVERED BY THE RULES", "App1": "OFFICIAL KATA LIST",
        "App2": "KATA COMPETITION CATEGORIES", "App3": "KATA PROTEST FORM",
        "App4": "SUMMARY TABLE OF WINNING CRITERIA AND TIE RESOLUTION",
    },
    "PARA": {
        "1": "PARA KARATE KATA COMPETITION", "2": "DISCIPLINE, CATEGORIES AND SPORT CLASSES",
        "3": "KATA COMPETITION AREA", "4": "OFFICIAL ATTIRE", "5": "ORGANISATION OF KATA COMPETITION",
        "6": "THE JUDGING PANEL", "7": "EVALUATION", "8": "OPERATION OF MATCHES", "9": "OFFICIAL PROTEST",
        "10": "ADAPTATION OF THESE RULES TO EVENTS OUTSIDE THE WKF OFFICIAL EVENT PROGRAMME",
        "11": "ISSUES NOT SPECIFICALLY COVERED BY THE RULES", "App1": "OFFICIAL KATA LIST",
        "App2": "KATA COMPETITION CATEGORIES", "App3": "KATA PROTEST FORM",
    },
}

# Tables and images that pdftotext cannot read cleanly, transcribed by hand from the PDFs.
SECTION_OVERRIDES = {
    ("KATA", "3.7.9"): "The following table shows allocation to groups for 32 down to 3 Athletes and determination "
        "of qualification from the Round-robin according to the next round: 8 groups (24-32 Athletes): the first "
        "of each Group qualify. 6 groups (18-23 Athletes): the first of each Group and the two best runner-ups "
        "qualify. 5 groups (17 Athletes): the first of each Group and the three best runner-ups qualify. 4 groups "
        "(12-16 Athletes): the first and runner-up of each Group. 3 groups (9-11 Athletes): the first and "
        "runner-up of each Group, as well as the best two number threes qualify. 2 groups (6-8 Athletes): the "
        "first and runner-up of each Group will compete directly in the semifinals. 1 group (3-5 Athletes): final "
        "between first and runner-up of the Group, and only one bronze medal bout. Groups hold 3 or 4 Athletes "
        "(5 in a single group of 5); seeds 1-4 are placed in groups 8, 4, 2 and 6.",
    ("KATA", "5.4.2"): "The winner is pointed out by each judge based on the relative marks that particular judge "
        "gave for each of the two Athletes or Teams. The winner is determined by the majority of votes by the Judges.",
    ("KATA", "5.6"): "Criteria for evaluation. Kata performance: 1. Stances 2. Techniques 3. Transitional movements "
        "4. Timing and synchronisation 5. Correct breathing 6. Focus (KIME) 7. Conformance: Consistence in the "
        "performance of the KIHON 8. Strength 9. Speed 10. Balance. Bunkai performance (applicable to Team "
        "performances for medals): 1. Stances 2. Techniques 3. Transitional movements 4. Timing & distance (MA-AI) "
        "5. Control 6. Focus (KIME) 7. Conformance (to Kata): Using the actual movements as performed in the Kata "
        "8. Strength 9. Speed 10. Balance.",
    ("KATA", "App1"): KATA_LIST_TEXT,
    ("KATA", "App4"): "Criteria for winning a bout or match (individual and Teams, Round-robin and elimination): "
        "1. Majority of votes from the Judges. Criteria for winning a Round-robin group and resolving ties - "
        "Individual: 1. Most Victory Points 2. Winner of the bout between the two 3. Most votes all judges, all "
        "bouts 4. Highest World Ranking 5. Extra bout - new kata. Teams: 1. Most Victory Points 2. Winner of the "
        "Match between the two 3. Most votes all judges, all matches 4. Extra match - new kata. For each pair "
        "compared the criteria must be considered from the beginning of the list. All winning criteria are listed "
        "in order of precedence from the top down.",
    ("PARA", "2.2"): "Para Karate Sport Classes. Sport Classes are competition subcategories that group Athletes "
        "with similar activity limitations resulting from their Eligible Impairment, to ensure fair and meaningful "
        "competition. Sport Classes offered in WKF events (Kata individuals, 16+): Visual Impairment - Male K10, "
        "Female K10: Athletes must meet the Minimum Impairment Criteria (MIC) for Visual Impairment; Extra Score "
        "(Compensation Score) is used to reflect the impact of the impairment on kata performance; Athletes "
        "compete standing; blindfolds are required for all Athletes during kata performance. Intellectual "
        "Impairment - Male K21, Male K22, Female K21, Female K22: Athletes must meet the MIC for Intellectual "
        "Impairment (K21: IQ below 75 and significant limitations in adaptive behaviour; K22: IQ below 75 plus an "
        "additional significant impairment); Athletes compete standing; Athletes may perform one kata; no Extra "
        "Score (Compensation Score) is used in this category - Athletes are judged solely on technical and "
        "athletic performance. Physical Impairment - Male K30, Female K30: Athletes must meet the MIC for Physical "
        "Impairment affecting lower limb and/or trunk function; Extra Score (Compensation Score) is used to "
        "reflect the impact of the impairment on kata performance; Athletes compete using wheelchairs. All MIC "
        "and eligibility decisions are made through the Classification process described in the WKF Para Karate "
        "Classification Rules, in accordance with the IPC Classification Code. Classification is held one or two "
        "days before the event.",
    ("PARA", "5.6.1"): "The number of Athletes will determine the number of groups to facilitate the elimination "
        "rounds. Number of Athletes / groups / kata performed to win / Athletes in the second round: 2 / 1 / 1 / "
        "zero (no second round); 3 / 1 / 2 / medal bout (only for gold); 4 / 2 / 2 / medal bout (only for gold); "
        "5 to 10 / 2 / 2 / medal bout; 11 to 24 / 2 / 3 / 8 Athletes; 25 to 48 / 4 / 4 / 16 Athletes; 49 to 96 / "
        "8 / 4 / 32 Athletes.",
    ("PARA", "5.6.9"): "The following table illustrates the competition format: first round (first kata) in groups "
        "of eight, the top four of each group go on to the next round; second round (second kata) the same; third "
        "round (third kata) in two groups, where 1st goes to the final and 2nd and 3rd go to the bronze (semi) "
        "finals; medal performances (fourth kata): final 1 versus 1 (winner 1st, loser 2nd) and two bronze finals "
        "2 versus 3 (winner 3rd, loser 5th).",
    ("PARA", "7.4.3"): "The system will eliminate the highest and lowest scores. Example: Judges 1-7 score 7.6, 7.6, "
        "8.2, 7.7, 7.5, 7.8, 8.1; Extra Score 1.2; Total 40.0.",
    ("PARA", "7.6"): "Criteria for evaluation. Judges apply the standard WKF Kata criteria (1. Stances 2. Techniques "
        "3. Transitional movements 4. Timing and synchronisation 5. Correct breathing 6. Focus (KIME) "
        "7. Conformance: Consistency in the performance of the KIHON 8. Strength 9. Speed 10. Balance), "
        "interpreted in light of the sport-class-specific guidance. K10 - Visually Impaired Athletes: recognisable "
        "embusen and orientation (start/finish area, main directions); stable stances, posture and balance without "
        "visual reference; precise, coordinated techniques in correct directions with clear endpoints. K21-K22 - "
        "Intellectually Impaired Athletes: complete kata with simple, consistent rhythm and limited unnecessary "
        "pauses; fluid transitions between techniques and stances; clear basic techniques with arms, legs and body "
        "moving in coordination. K30 - Physically Impaired Athletes (wheelchair users): controlled, purposeful "
        "wheelchair movement following the general kata line; controlled posture and trunk alignment within the "
        "Athlete's functional abilities, with clear upper-body techniques and kime; coordination between "
        "wheelchair motion and technique execution (e.g. stopping/turning in time with techniques).",
    ("PARA", "App1"): KATA_LIST_TEXT,
}
# Title-line spill-over and empty/duplicate fragments produced by the parser.
DROP_SECTIONS = {("KATA", "9", "EVENT PROGRAMME"), ("PARA", "10", "EVENT PROGRAMME"), ("PARA", "5.6.10", "")}


def pdf_pages(path):
    return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=True).stdout.split("\f")


def parse_rules(path, doc):
    arts, secs, art = [], [], None
    for pi, page in enumerate(pdf_pages(path), start=1):
        for ln in page.split("\n"):
            s = ln.strip()
            if not s or s.startswith("Rules Version"):
                continue
            m = re.match(r"^(ARTICLE|APPENDIX)\s+(\d+)\s*:", s)
            if m and pi >= 3:
                art = m.group(2) if m.group(1) == "ARTICLE" else "App" + m.group(2)
                arts.append((doc, art, ARTICLE_TITLES[doc][art], pi))
                continue
            if art is None:
                continue
            m = re.match(r"^(\d+)\.\s?(\d+(?:\.\d+)*)\.?(?:\s+(.*))?$", s)
            indent = len(ln) - len(ln.lstrip())
            # a new section: numbered with the current article, near the margin, followed by words rather than
            # more numbers (so score rows like "7.6 8.2 7.7" in Para 7.4.3 or "5.0 represents" stay as text)
            if (m and not art.startswith("App") and m.group(1) == art and indent <= 12
                    and not re.match(r"^\d+\.0\b", s) and not re.match(r"\d", m.group(3) or "")):
                secs.append([doc, art, m.group(1) + "." + m.group(2), m.group(3) or "", pi])
            elif secs and secs[-1][1] == art:
                secs[-1][3] += " " + s
            else:
                secs.append([doc, art, art, s, pi])
    if doc == "KATA":  # Appendix 4 is an image with no extractable text
        secs.append([doc, "App4", "App4", "", next(a[3] for a in arts if a[1] == "App4")])
    out = []
    for d, a, n, text, page in secs:
        text = re.sub(r"\s+", " ", text).strip()
        if (d, n, text) in DROP_SECTIONS:
            continue
        out.append((d, a, n, SECTION_OVERRIDES.get((d, n), text), page))
    return arts, out


def parse_questions(path):
    words = r"\S+(?: {1,2}\S+)*"  # a run of text; columns are separated by 3+ spaces
    qs, cur = {}, None
    for page in pdf_pages(path):
        lines = page.split("\n")
        starts = []
        for ln in lines:
            if re.match(r"^\d{1,3}\s", ln):
                fields = [f.start() for f in re.finditer(words, ln)]
                if len(fields) == 4:
                    starts.append(fields[1:])
        if not starts:
            continue
        cols = [sorted(s[i] for s in starts)[len(starts) // 2] for i in range(3)]
        for ln in lines:
            if not ln.strip() or ln.strip().startswith(("No.", "Version")):
                continue
            m = re.match(r"^(\d{1,3})\s", ln)
            if m and int(m.group(1)) == (cur or 0) + 1:
                cur = int(m.group(1))
                qs[cur] = [[], [], []]
                ln = " " * len(m.group(1)) + ln[len(m.group(1)):]
            if cur is None:
                continue
            for f in re.finditer(words, ln):
                col = min(range(3), key=lambda k: abs(cols[k] - f.start()))
                qs[cur][col].append(f.group())

    def join(parts):
        s = ""
        for p in parts:
            s = s + p if s.endswith("-") and not s.endswith(" -") and p[:1].islower() else (s + " " + p if s else p)
        return re.sub(r"\s+", " ", s).strip()

    return {n: tuple(join(c) for c in v) for n, v in qs.items()}


# (num, answer, rule_ref, explanation). "Art." = WKF Kata Rules 2026; "Para Art." = WKF Para Karate Kata Rules 2026.
ANSWERS = [
    (1, "FALSE", "Art. 2.2.1(a)", "There is no WKF requirement for Team members to wear the same brand of Karategi."),
    (2, "FALSE", "Art. 3.5.6", "The combined Kata & Bunkai time limit is 5 minutes, not 6."),
    (3, "TRUE", "Art. 5.3.2", "Slight variation as taught by the Athlete's style (Ryu-ha) is permitted."),
    (4, "TRUE", "Art. 2.2.4", "Glasses are forbidden (prescription sport-glasses or soft contact lenses may be worn at own risk)."),
    (5, "FALSE", "Art. 2.2.6", "One OR TWO discreet rubber bands on a single ponytail are permitted, not only one."),
    (6, "TRUE", "Art. 3.3.1", "Kata competition can be organised in several ways (elimination with repechage, Round-robin + elimination, two-pool Round-robin)."),
    (7, "FALSE", "Art. 3.7.2 / 3.7.9", "Round-robin categories take up to 32 Athletes (8 groups of 4); there is no cap of 8."),
    (8, "TRUE", "Art. 3.3.2 / 3.5.1", "Teams have 3 or 4 Athletes, of which 3 compete at a time."),
    (9, "TRUE", "Art. 5.6 (criterion 7)", "Conformance is defined as consistence in the performance of the KIHON."),
    (10, "FALSE", "Art. 6.3 / App. 1", "On a number/name discrepancy the NUMBER on the official Kata list prevails, not the name."),
    (11, "FALSE", "Art. 5.7 (foul 5)", "Audible cues from any other person, including other Team members, to guide tempo are a foul, so a team member's start/finish command is an external cue."),
    (12, "FALSE", "Art. 1.1 / 1.5", "Art. 1.1 only requires a WKF Approved matted 8 m square; the 1.5 illustration shows the standard two-colour tatami, so a uniform colour is not required."),
    (13, "TRUE", "Art. 5.3.2 / 5.6", "Judges assess the Kihon (conformance) as taught by the Athlete's own style; style variations are permitted."),
    (14, "TRUE", "Art. 4.1", "Judges are designated by random computer selection for each round, so the panel can change every round."),
    (15, "TRUE", "Art. 3.5.6", "The total time allowed for Kata & Bunkai combined is 5 minutes."),
    (16, "TRUE", "Art. 2.2.1(k)", "Jacket sleeves may not be rolled up."),
    (17, "TRUE", "Art. 6.1 / 6.2", "The chosen Kata is submitted to the Runner before each round; ensuring it is correct is the Coach's (or, without a Coach, the Athlete's) responsibility."),
    (18, "FALSE", "Art. 4.1 / 4.4", "Five Judges are used for eliminations (and flag judging), but Round-robin rounds and medal bouts must have seven, so not for any competition."),
    (19, "FALSE", "Art. 5.2.1", "A kata may be repeated (not twice in a row, at most twice per competition); the tiebreaker-only rule is Para Karate K10/K30 (Para Art. 7.2.1)."),
    (20, "FALSE", "Art. 2.2.1(l)", "Trousers must cover at least two thirds of the shin."),
    (21, "TRUE", "Art. 5.7 (foul 7)", "Incorrect Kiai is listed as a foul."),
    (22, "FALSE", "Para Art. 5.6.1 / 5.6.3-5.6.4", "Only with 2 Athletes is a single kata performed; with 3 Athletes two kata are needed (a group round, then the top two meet for 1st/2nd)."),
    (23, "TRUE", "Art. 4.8", "Judges must not have the nationality of, or be from the same NF as, either participant."),
    (24, "FALSE", "Art. 2.2.6", "Ribbons, beads and other decorations are prohibited in Kata as well."),
    (25, "TRUE", "Art. 3.5.4", "In Team Kata medal bouts, teams perform the Kata and then a demonstration of its meaning (Bunkai)."),
    (26, "FALSE", "Art. 5.2.1", "Kata can be repeated in any format: not twice in a row and no more than twice per competition."),
    (27, "FALSE", "Art. 4.1 / 4.9", "Panels are seven or five Judges (five for eliminations and flag judging); never reduced to three."),
    (28, "TRUE", "Art. 5.2.1", "Any kata may be performed in the medal round, unless already performed twice."),
    (29, "TRUE", "Art. 3.7.8", "The scheduled first-round opponent advances by bye (walkover)."),
    (30, "FALSE", "Art. 2.2.1(h)", "Female Athletes CAN wear a plain white T-shirt; it is optional, not mandatory."),
    (31, "TRUE", "Art. 2.2.1(h)", "Female Athletes can wear a plain white T-shirt beneath the jacket."),
    (32, "TRUE", "Art. 2.2.7", "The wearing of any unauthorised apparel, clothing or equipment is forbidden."),
    (33, "TRUE", "Art. 2.2.6", "One or two discreet rubber bands on a single ponytail are permitted."),
    (34, "FALSE", "Art. 1.1 / 1.5", "Kata uses the same WKF Approved 8 m matted square as Kumite (see the Art. 1.5 illustration)."),
    (35, "FALSE", "Art. 2.2.1(i) / 2.2.7", "The jacket ties must be tied at the start of the performance; nothing permits removing the jacket."),
    (36, "TRUE", "Art. 5.7 (foul 6)", "Theatrics are very serious fouls, on the same level as a major loss of balance."),
    (37, "FALSE", "Art. 5.3.2", "Slight variation as taught by the Athlete's style (Ryu-ha) IS permitted."),
    (38, "TRUE", "Art. 6.1", "Before each round the chosen Kata must be submitted to the assigned Runners."),
    (39, "TRUE", "Art. 5.8 (DQ 2) / 5.3.1", "In team medal matches the performance ends with the bow after the Bunkai; failing to bow at completion is a disqualification ground."),
    (40, "TRUE", "Art. 5.2.1 / 3.7.9", "A different kata is required for each round, and the number of rounds depends on the number of entries."),
    (41, "FALSE", "Art. 5.8 (DQ 11) / 3.7.8", "SHIKKAKU is disqualification for misconduct; a SHIKKAKU Athlete cannot progress (the opponent advances) and is not awarded a medal."),
    (42, "TRUE", "Art. 5.6", "Performances are evaluated on all the listed criteria."),
    (43, "TRUE", "Art. 3.9", "No specific deviations for under-14s, but the Kata list may be limited to less advanced Kata."),
    (44, "TRUE", "Art. 5.7 (foul 10)", "Causing injury by lack of controlled technique during Bunkai is a foul."),
    (45, "FALSE", "Art. 4.8", "No Judge may share the nationality or NF of either participant, including in medal bouts."),
    (46, "TRUE", "Art. 5.4.1", "Scores use a 5.0 to 10.0 scale in increments of 0.1 (0.0 indicates disqualification)."),
    (47, "FALSE", "Art. 5.11 / 5.12 / App. 4", "Ties are resolved by victory points, head-to-head, judges' votes, ranking and an extra kata; there is no coin toss."),
    (48, "FALSE", "Art. 5.11 / App. 4", "Individual Round-robin groups use 5 criteria, not 6."),
    (49, "TRUE", "Art. 5.6 (criterion 8)", "Strength is an evaluation criterion."),
    (50, "FALSE", "Art. 5.10 / App. 4", "In the elimination system the winner is simply the majority of Judges' votes; there are no 6 tie criteria."),
    (51, "TRUE", "Art. 5.6", "There are 10 evaluation criteria."),
    (52, "FALSE", "Art. 5.6", "Transitional movements are criterion 3 for both Kata and Bunkai."),
    (53, "TRUE", "Art. 5.6", "Bunkai criteria include transitional movements (3) and control (5)."),
    (54, "TRUE", "Art. 5.6", "Strength (8), speed (9) and balance (10) apply to both Kata and Bunkai."),
    (55, "TRUE", "Art. 5.7 (foul 11)", "Simulated unconsciousness for more than 2 seconds during Bunkai is a foul."),
    (56, "TRUE", "Art. 5.4.3", "Bunkai is to be given equal importance as the Kata itself."),
    (57, "TRUE", "Art. 5.7 (foul 9)", "Time wasting, including excessive bowing, is a foul."),
    (58, "FALSE", "Art. 5.7 (foul 10) / 5.8", "Causing injury in Bunkai is a foul, not a disqualification (only a scissor takedown to the neck is a DQ)."),
    (59, "FALSE", "Art. 5.8 (DQ 1)", "Not announcing the kata is a disqualification ground."),
    (60, "TRUE", "Art. 5.8 (DQ 1)", "Announcing the wrong kata or performing a kata other than pre-announced is a disqualification ground."),
    (61, "TRUE", "Art. 5.7 (foul 6)", "Stamping, slapping the chest, arms or Karategi are theatrics, a very serious foul."),
    (62, "FALSE", "Art. 5.8 (DQ 4)", "A distinct pause or stop in the performance is a disqualification ground."),
    (63, "FALSE", "Art. 5.4.3", "Bunkai IS given equal importance as the Kata."),
    (64, "TRUE", "Art. 5.8 (DQ 3) / 6.8", "Not starting the Kata facing the Judges is a disqualification ground."),
    (65, "TRUE", "Art. 5.7 (foul 5)", "Audible cues from any other person, including other Team members, are a foul."),
    (66, "TRUE", "Art. 5.8 (DQ 8)", "The belt falling off during the performance is a disqualification ground."),
    (67, "FALSE", "Art. 5.8 (DQ 11)", "Failure to follow the Chief Judge's instructions or other misconduct is a disqualification (SHIKKAKU), not a foul."),
    (68, "TRUE", "Art. 5.8 (DQ 11)", "Failure to follow the Chief Judge's instructions or other misconduct leads to disqualification (SHIKKAKU)."),
    (69, "FALSE", "Art. 5.8 (DQ 9)", "Exceeding the 5-minute Kata + Bunkai limit is a disqualification, not a foul."),
    (70, "FALSE", "Art. 3.5.2", "Team members must START facing the same direction towards the Judges; the rule says nothing about finishing."),
    (71, "TRUE", "Art. 3.1.1", "Kata must be realistic in fighting terms and display concentration, power, and potential impact."),
    (72, "FALSE", "Art. 5.7 (foul 10)", "Causing injury by lack of control in Bunkai IS a foul."),
    (73, "FALSE", "Art. 5.7 (foul 2)", "Minor loss of balance is a foul that must be considered."),
    (74, "TRUE", "Art. 5.8 (DQ 9)", "Exceeding the 5-minute Kata + Bunkai limit is a disqualification ground."),
    (75, "TRUE", "Art. 3.1.1", "Kata must demonstrate strength, power, and speed, as well as grace, rhythm, and balance."),
    (76, "TRUE", "Art. 5.7 (foul 2)", "Minor loss of balance is a foul that must be considered."),
    (77, "TRUE", "Art. 5.7 (foul 4)", "Delivering a technique before the body transition is completed is an asynchronous-movement foul."),
    (78, "TRUE", "Art. 5.7 (foul 6)", "Inappropriate exhalation is theatrics, a very serious foul."),
    (79, "FALSE", "Art. 5.7 (foul 4)", "Failing to do a movement in unison in Team Kata IS a foul."),
    (80, "TRUE", "Art. 5.7 (foul 3)", "Performing a movement in an incorrect or incomplete manner is a foul."),
    (81, "TRUE", "Art. 5.7 (foul 9)", "Time wasting (prolonged marching, excessive bowing, prolonged pause) is a foul."),
    (82, "TRUE", "Art. 5.7 (foul 6)", "Stamping the feet and slapping the chest, arms or Karategi are given as examples of theatrics."),
    (83, "FALSE", "Art. 5.7 (foul 6)", "Theatrics are a very serious foul."),
    (84, "FALSE", "Art. 5.7 (foul 6)", "Inappropriate exhalation is listed among the theatrics."),
    (85, "TRUE", "Art. 5.7 (foul 3)", "Failure to fully execute a block or punching off target is a foul."),
    (86, "FALSE", "Art. 5.7 (foul 10)", "Causing injury by lack of control in Bunkai is a foul, not allowed."),
    (87, "TRUE", "Art. 3.5.3", "Team members must demonstrate competence in all aspects of the Kata as well as synchronisation."),
    (88, "TRUE", "Art. 5.7 (foul 5)", "Audible cues (such as start/stop commands) from any other person, including Team members, are a foul the Judges consider."),
    (89, "FALSE", "Art. 6.2", "It is the sole responsibility of the Coach (or, without a Coach, the Athlete or Team), not the NF President."),
    (90, "TRUE", "Art. 3.5.8", "After being downed in Bunkai the Athlete should rise to one knee or stand within 2 seconds."),
    (91, "TRUE", "Art. 5.8 (DQ 5)", "Omitting or adding movements, or substantially changing the Kata, is a disqualification ground."),
    (92, "FALSE", "Art. 5.9.1 / Kumite Art. 10.5", "In both Kata and Kumite excessive celebration is prohibited and subject to a fine; it is not a disqualification in Kumite."),
    (93, "TRUE", "Art. 5.1.1", "Only Kata from the WKF official Kata list may be performed."),
    (94, "TRUE", "Art. 5.8 (DQ 2)", "Failing to bow at the beginning and completion of the performance is a disqualification ground."),
    (95, "FALSE", "Art. 2.2.7", "Unauthorised apparel, clothing or equipment is forbidden; weapons and ancillary equipment are not allowed."),
    (96, "TRUE", "Art. 5.3.1", "The performance is evaluated from the bow starting the Kata until the bow ending the Kata."),
    (97, "TRUE", "Art. 5.7 (foul 8)", "A belt coming loose to the extent that it is coming off the hips is a foul."),
    (98, "FALSE", "Art. 5.7 (foul 8) / 5.8 (DQ 8)", "A belt coming off the hips is a foul; only a belt falling off is a disqualification."),
    (99, "TRUE", "Art. 6.7", "After the bow the Athlete must clearly announce the Kata name and then start."),
    (100, "FALSE", "Art. 5.6", "There are 10 evaluation criteria, not 9."),
    (101, "TRUE", "Art. 3.5.9", "Kani Basami to the neck is prohibited in Bunkai; to the body or legs it is permitted."),
    (102, "FALSE", "Art. 3.5.9 / 5.8 (DQ 10)", "Kani Basami to the neck is prohibited and a disqualification ground."),
    (103, "TRUE", "Art. 5.7 (foul 6)", "Theatrics must be considered very serious fouls."),
    (104, "FALSE", "Art. 7.1.5 / 7.1.10", "The Coach delivers the protest to the Tatami Manager; the Tatami Manager submits it to the Appeals Jury representative."),
    (105, "TRUE", "Art. 7.3.1", "The receiving Tatami Manager gathers the Appeals Jury and deposits the protest sum with WKF for a declined protest."),
    (106, "TRUE", "Art. 7.3.3", "Each of the three members must give a verdict; abstentions are not acceptable."),
    (107, "FALSE", "Para Art. 4.6.11(a)", "Sponsor logos or advertising are prohibited on the wheelchair backrest."),
    (108, "TRUE", "Art. 7.4.2", "An accepted protest is verbally notified by one appointed member of the Appeals Jury."),
    (109, "TRUE", "Para Art. 2.1.1", "The categories are Visual, Intellectual and Physical Impairment."),
    (110, "FALSE", "Para Art. 4.4.4 / 4.4.5", "Prostheses (except eyes), canes, crutches and other physical-support equipment are not allowed in competition."),
    (111, "TRUE", "Para Art. 2.1.3", "Athletes with more than one Eligible Impairment may compete in only one Sport Class per championship."),
    (112, "FALSE", "Para Art. 7.4.1 / 7.4.2", "Judges score the performance only; the Compensation Score for the impairment is issued by the Classification Panel."),
    (113, "FALSE", "Para Art. 2.1.1", "Para Karate competitions include Individual Kata only."),
    (114, "TRUE", "Para Art. 4.6.7.3(b)", "One or two anti-tip castors at the back of the wheelchair are permitted."),
    (115, "FALSE", "Para Art. 2.1.4 / 2.2", "A Compensation Score applies only to K10 and K30; K21/K22 have none."),
    (116, "TRUE", "Para Art. 7.9", "Potential reasons for disqualification must be treated with particular care because impairments can influence movement or behaviour."),
    (117, "FALSE", "Para Art. 4.2.7 / 4.4.3", "Nothing in the Para rules permits sport shoes; accepted accessory equipment is blindfolds, sports glasses and leg straps only."),
    (118, "TRUE", "Para Art. 4.8.5", "The National Coaches are directly responsible for the safe removal of their Athletes."),
    (119, "TRUE", "Para Art. 7.2.2", "K21/K22 Athletes may perform the same Kata in each round."),
    (120, "FALSE", "Para Art. 4.7.4", "Certified medical service animals ARE allowed at the external perimeter (but not in the Competition Area)."),
    (121, "TRUE", "Art. 7.5.1", "The Appeals Jury elaborates a simple protest incident report stating its findings and reasons."),
    (122, "FALSE", "App. 1", "The official WKF Kata list has 102 Kata."),
    (123, "FALSE", "Para Art. 7.7", "Para Karate has its own tie-resolution steps based on scores (6 of 7 Judges, then all 7), World Ranking, then a repeat Kata."),
    (124, "FALSE", "Para Art. 4.7.5", "Therapy or emotional-support animals are not permitted in the Competition Area or its perimeter."),
    (125, "FALSE", "Para Art. 4.5.4", "Blindfolds must not have any logos or markings of sponsors."),
    (126, "FALSE", "Para Art. 4.6.6.2", "Leg straps must be made from material that is not elastic or otherwise stretchable."),
    (127, "FALSE", "Para Art. 7.4.2", "Extra Points are issued by the Classification Panel, not given by the Judges."),
    (128, "FALSE", "Para Art. 2.1.1 / 2.2", "There are four Sport Classes: K10, K21, K22 and K30 (three categories)."),
    (129, "FALSE", "Para Art. 2.1.1 / 2.2", "Visually impaired Athletes form a single Sport Class, K10."),
    (130, "TRUE", "Para Art. 2.2 / 4.5.3", "Blindfolds are required for all K10 Athletes during the kata performance."),
    (131, "TRUE", "Para Art. 2.2", "Intellectually impaired Athletes (K21/K22) compete standing."),
    (132, "FALSE", "Para Art. 7.2.2", "K21/K22 Athletes may perform the same Kata in each round; repetition is allowed."),
]


def main():
    arts, secs = [], []
    for path, doc in ((KATA_RULES_PDF, "KATA"), (PARA_RULES_PDF, "PARA")):
        a, s = parse_rules(path, doc)
        arts += a
        secs += s
    questions = parse_questions(QUESTIONS_PDF)
    answers = {a[0]: a[1:] for a in ANSWERS}
    assert sorted(questions) == sorted(answers) == list(range(1, 133)), "question/answer numbering mismatch"

    con = sqlite3.connect(DB)
    con.executescript("""
    DROP TABLE IF EXISTS kata_questions;
    DROP TABLE IF EXISTS kata_rule_sections;
    DROP TABLE IF EXISTS kata_articles;
    CREATE TABLE kata_articles (
        doc TEXT,             -- 'KATA' (WKF Kata Rules 2026) or 'PARA' (WKF Para Karate Kata Rules 2026)
        article_no TEXT,
        title TEXT,
        page INTEGER,
        PRIMARY KEY (doc, article_no)
    );
    CREATE TABLE kata_rule_sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc TEXT,
        article_no TEXT,
        section_no TEXT,
        text TEXT,
        page INTEGER,
        FOREIGN KEY(doc, article_no) REFERENCES kata_articles(doc, article_no)
    );
    CREATE TABLE kata_questions (
        num INTEGER PRIMARY KEY,
        en TEXT,
        fr TEXT,
        es TEXT,
        answer TEXT,          -- 'TRUE' or 'FALSE'
        rule_ref TEXT,        -- "Art. ..." = Kata Rules, "Para Art. ..." = Para Karate Rules
        explanation TEXT
    );
    """)
    con.executemany("INSERT INTO kata_articles VALUES (?,?,?,?)", arts)
    con.executemany("INSERT INTO kata_rule_sections (doc, article_no, section_no, text, page) VALUES (?,?,?,?,?)", secs)
    con.executemany("INSERT INTO kata_questions VALUES (?,?,?,?,?,?,?)",
                    [(n, *questions[n], *answers[n]) for n in sorted(questions)])
    con.commit()
    print(f"{len(arts)} articles, {len(secs)} sections, {len(questions)} questions")
    export_js(con)


def export_js(con):
    """Write the KATA_* arrays into data.js (and site/data.js) next to the Kumite arrays.

    Para Karate articles get a "P" prefix (Para Art. 7 -> "P7", Para Appendix 1 -> "PApp1") so both rulebooks
    share one article namespace on the site. Unnumbered sections (appendices, Art. 10) use the article key.
    """
    def key(doc, article_no):
        return ("P" if doc == "PARA" else "") + article_no

    articles = [{"article_no": key(d, a), "title": t, "page": p}
                for d, a, t, p in con.execute("SELECT doc, article_no, title, page FROM kata_articles "
                                              "ORDER BY doc, rowid")]
    sections = []
    for d, a, n, t, p in con.execute("SELECT doc, article_no, section_no, text, page FROM kata_rule_sections ORDER BY id"):
        sections.append({"article_no": key(d, a), "section_no": key(d, n) if n == a else n, "text": t, "page": p})
    questions = [dict(zip(("num", "en", "fr", "es", "answer", "rule_ref", "explanation"), r))
                 for r in con.execute("SELECT num, en, fr, es, answer, rule_ref, explanation FROM kata_questions "
                                      "ORDER BY num")]
    lines = [ln for ln in open("data.js", encoding="utf-8").read().splitlines() if not ln.startswith("const KATA_")]
    for name, value in (("KATA_QUESTIONS", questions), ("KATA_ARTICLES", articles), ("KATA_SECTIONS", sections)):
        lines.append(f"const {name} = {json.dumps(value, ensure_ascii=False)};")
    for path in ("data.js", "site/data.js"):
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    print("wrote KATA_* to data.js and site/data.js")


if __name__ == "__main__":
    main()
