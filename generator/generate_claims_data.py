#!/usr/bin/env python3
"""
Practice healthcare claims dataset generator (self-funded employer plans / TPA style).

Everything in here is fake: people, employers, providers, NPIs and dollar amounts.
The same seed always produces the same files, so the dataset can be rebuilt any time:

    python3 generate_claims_data.py data

Extract date: 2026-10-15. Claims received through 2026-10-14.
Service dates: 2025-01-01 through 2026-09-30.
"""
import csv
import json
import math
import os
import random
import sys
from collections import defaultdict
from datetime import date, timedelta

SEED = 20261024
R = random.Random(SEED)
OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
SPOILERS = sys.argv[2] if len(sys.argv) > 2 else None

AS_OF = date(2026, 10, 14)          # last receipt date in the extract
FINAL_CUTOFF = AS_OF - timedelta(days=3)   # processed after this = still pended
SVC_START = date(2025, 1, 1)
SVC_END = date(2026, 9, 30)
OPEN_END = date(9999, 12, 31)

PLANT = defaultdict(list)           # planted data problems, for the answer key

# --------------------------------------------------------------------------- helpers

def d(y, m, dd):
    return date(y, m, dd)


def rdate(a, b):
    if b < a:
        return a
    return a + timedelta(days=R.randint(0, (b - a).days))


def first_of_month(x):
    return date(x.year, x.month, 1)


def add_months(x, n):
    y, m = x.year, x.month + n
    while m > 12:
        y, m = y + 1, m - 12
    while m < 1:
        y, m = y - 1, m + 12
    return date(y, m, 1)


def month_end(x):
    return add_months(x, 1) - timedelta(days=1)


def money(x):
    return round(x + 1e-9, 2)


def poisson(lam):
    if lam <= 0:
        return 0
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= R.random()
        if p <= L:
            return k
        k += 1


def wchoice(pairs):
    tot = sum(w for _, w in pairs)
    x = R.random() * tot
    for v, w in pairs:
        x -= w
        if x <= 0:
            return v
    return pairs[-1][0]


def age_on(dob, on):
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


# --------------------------------------------------------------------------- reference data

PROCS = [
    # code, description (plain English, not official descriptors), category, 2025 in-network fee
    ("99202", "New patient office visit, straightforward", "Office Visit", 95.00),
    ("99203", "New patient office visit, low complexity", "Office Visit", 140.00),
    ("99204", "New patient office visit, moderate complexity", "Office Visit", 210.00),
    ("99205", "New patient office visit, high complexity", "Office Visit", 275.00),
    ("99211", "Established patient visit, minimal (nurse visit)", "Office Visit", 30.00),
    ("99212", "Established patient office visit, straightforward", "Office Visit", 75.00),
    ("99213", "Established patient office visit, low complexity", "Office Visit", 115.00),
    ("99214", "Established patient office visit, moderate complexity", "Office Visit", 165.00),
    ("99215", "Established patient office visit, high complexity", "Office Visit", 230.00),
    ("99391", "Preventive visit, established patient, under age 1", "Preventive", 160.00),
    ("99392", "Preventive visit, established patient, age 1-4", "Preventive", 170.00),
    ("99393", "Preventive visit, established patient, age 5-11", "Preventive", 170.00),
    ("99394", "Preventive visit, established patient, age 12-17", "Preventive", 180.00),
    ("99395", "Preventive visit, established patient, age 18-39", "Preventive", 185.00),
    ("99396", "Preventive visit, established patient, age 40-64", "Preventive", 200.00),
    ("99397", "Preventive visit, established patient, age 65+", "Preventive", 210.00),
    ("99283", "Emergency department visit, moderate severity", "Emergency", 140.00),
    ("99284", "Emergency department visit, moderately high severity", "Emergency", 230.00),
    ("99285", "Emergency department visit, high severity", "Emergency", 330.00),
    ("99223", "Initial hospital inpatient care, high complexity", "Inpatient Visit", 270.00),
    ("99232", "Subsequent hospital inpatient care, moderate complexity", "Inpatient Visit", 110.00),
    ("99238", "Hospital discharge day management", "Inpatient Visit", 110.00),
    ("99460", "Initial newborn care in hospital", "Inpatient Visit", 150.00),
    ("36415", "Routine blood draw (venipuncture)", "Lab", 8.00),
    ("80053", "Comprehensive metabolic panel", "Lab", 18.00),
    ("80061", "Lipid panel", "Lab", 22.00),
    ("83036", "Hemoglobin A1c", "Lab", 16.00),
    ("84443", "Thyroid stimulating hormone (TSH)", "Lab", 28.00),
    ("85025", "Complete blood count with differential", "Lab", 13.00),
    ("81002", "Urinalysis, dipstick, no microscopy", "Lab", 5.00),
    ("87804", "Rapid influenza test", "Lab", 22.00),
    ("87880", "Rapid strep test", "Lab", 20.00),
    ("87635", "COVID-19 PCR test", "Lab", 65.00),
    ("71046", "Chest X-ray, 2 views", "Radiology", 45.00),
    ("73562", "Knee X-ray, 3 views", "Radiology", 50.00),
    ("73610", "Ankle X-ray, 3 views", "Radiology", 45.00),
    ("72148", "MRI lumbar spine without contrast", "Radiology", 520.00),
    ("73721", "MRI knee without contrast", "Radiology", 520.00),
    ("70450", "CT head without contrast", "Radiology", 210.00),
    ("74177", "CT abdomen and pelvis with contrast", "Radiology", 420.00),
    ("77067", "Screening mammogram, both breasts", "Preventive", 175.00),
    ("76805", "Obstetric ultrasound after first trimester", "Maternity", 240.00),
    ("59025", "Fetal non-stress test", "Maternity", 70.00),
    ("59400", "Routine obstetric care with vaginal delivery (global)", "Maternity", 3600.00),
    ("93000", "Electrocardiogram (ECG) with interpretation", "Cardiology", 25.00),
    ("93306", "Echocardiogram, complete with Doppler", "Cardiology", 360.00),
    ("20610", "Joint injection or aspiration, major joint", "Surgery", 85.00),
    ("29881", "Knee arthroscopy with meniscus repair/removal", "Surgery", 1150.00),
    ("27447", "Total knee replacement", "Surgery", 2100.00),
    ("47562", "Laparoscopic gallbladder removal", "Surgery", 1400.00),
    ("45378", "Colonoscopy, diagnostic or screening", "Surgery", 480.00),
    ("45380", "Colonoscopy with biopsy", "Surgery", 560.00),
    ("97161", "Physical therapy evaluation, low complexity", "Physical Therapy", 110.00),
    ("97110", "Therapeutic exercise, each 15 minutes", "Physical Therapy", 38.00),
    ("97140", "Manual therapy, each 15 minutes", "Physical Therapy", 35.00),
    ("90791", "Psychiatric diagnostic evaluation", "Behavioral Health", 210.00),
    ("90834", "Psychotherapy, 45 minutes", "Behavioral Health", 125.00),
    ("90837", "Psychotherapy, 60 minutes", "Behavioral Health", 165.00),
    ("90471", "Vaccine administration, first vaccine", "Immunization", 25.00),
    ("90686", "Flu vaccine, preservative-free", "Immunization", 28.00),
    ("96413", "Chemotherapy IV infusion, first hour", "Oncology", 290.00),
    ("96415", "Chemotherapy IV infusion, each additional hour", "Oncology", 60.00),
    ("J9271", "Pembrolizumab injection, per 1 mg", "Drug", 58.00),
    ("J0696", "Ceftriaxone injection, per 250 mg", "Drug", 6.00),
    ("J1100", "Dexamethasone injection, per 1 mg", "Drug", 1.00),
]
FEE_SCALE = 1.15
PROCS = [(c, desc, cat, round(f * FEE_SCALE, 2)) for c, desc, cat, f in PROCS]
FEES = {c: f for c, _, _, f in PROCS}
PCAT = {c: cat for c, _, cat, _ in PROCS}

REVS = [
    ("0120", "Room and board, semi-private"),
    ("0170", "Nursery"),
    ("0200", "Intensive care"),
    ("0250", "Pharmacy"),
    ("0260", "IV therapy"),
    ("0270", "Medical/surgical supplies"),
    ("0300", "Laboratory"),
    ("0320", "Diagnostic X-ray"),
    ("0350", "CT scan"),
    ("0360", "Operating room services"),
    ("0410", "Respiratory therapy"),
    ("0450", "Emergency room"),
    ("0480", "Cardiology"),
    ("0490", "Ambulatory surgical care"),
    ("0610", "MRI"),
    ("0636", "Drugs requiring detailed coding"),
    ("0710", "Recovery room"),
    ("0720", "Labor and delivery room"),
    ("0730", "EKG/ECG"),
]

DX = [
    ("Z00.00", "Adult general exam, no abnormal findings", "Preventive"),
    ("Z00.01", "Adult general exam, with abnormal findings", "Preventive"),
    ("Z00.129", "Routine child health exam, no abnormal findings", "Preventive"),
    ("Z23", "Encounter for immunization", "Preventive"),
    ("Z12.31", "Screening mammogram for breast cancer", "Preventive"),
    ("Z12.11", "Screening for colon cancer", "Preventive"),
    ("Z34.90", "Supervision of normal pregnancy", "Maternity"),
    ("O80", "Full-term uncomplicated delivery", "Maternity"),
    ("Z38.00", "Single liveborn infant, born in hospital, vaginal delivery", "Newborn"),
    ("E11.9", "Type 2 diabetes without complications", "Chronic"),
    ("E11.65", "Type 2 diabetes with high blood sugar", "Chronic"),
    ("R73.03", "Prediabetes", "Chronic"),
    ("I10", "High blood pressure (essential hypertension)", "Chronic"),
    ("E78.5", "High cholesterol (hyperlipidemia), unspecified", "Chronic"),
    ("E03.9", "Hypothyroidism, unspecified", "Chronic"),
    ("E66.9", "Obesity, unspecified", "Chronic"),
    ("J45.909", "Asthma, uncomplicated", "Chronic"),
    ("J44.9", "COPD, unspecified", "Chronic"),
    ("K21.9", "Acid reflux (GERD) without esophagitis", "Chronic"),
    ("I25.10", "Coronary artery disease without angina", "Cardiac"),
    ("I48.91", "Atrial fibrillation, unspecified", "Cardiac"),
    ("I50.9", "Heart failure, unspecified", "Cardiac"),
    ("R07.9", "Chest pain, unspecified", "Symptom"),
    ("R05.9", "Cough, unspecified", "Symptom"),
    ("R10.9", "Abdominal pain, unspecified", "Symptom"),
    ("R51.9", "Headache, unspecified", "Symptom"),
    ("F41.1", "Generalized anxiety disorder", "Behavioral Health"),
    ("F32.A", "Depression, unspecified", "Behavioral Health"),
    ("F90.2", "ADHD, combined type", "Behavioral Health"),
    ("J06.9", "Acute upper respiratory infection", "Acute"),
    ("J02.9", "Sore throat (acute pharyngitis)", "Acute"),
    ("J02.0", "Strep throat", "Acute"),
    ("J11.1", "Influenza with respiratory symptoms", "Acute"),
    ("U07.1", "COVID-19", "Acute"),
    ("H66.90", "Ear infection (otitis media), unspecified ear", "Acute"),
    ("H10.9", "Pink eye (conjunctivitis), unspecified", "Acute"),
    ("N39.0", "Urinary tract infection", "Acute"),
    ("L03.90", "Cellulitis, unspecified", "Acute"),
    ("J18.9", "Pneumonia, unspecified organism", "Acute"),
    ("S93.401A", "Right ankle sprain, initial encounter", "Injury"),
    ("G43.909", "Migraine, unspecified", "Neurological"),
    ("K80.20", "Gallstones without inflammation or blockage", "Digestive"),
    ("K57.30", "Diverticulosis of large intestine", "Digestive"),
    ("M54.50", "Low back pain, unspecified", "Musculoskeletal"),
    ("M25.561", "Pain in right knee", "Musculoskeletal"),
    ("M25.562", "Pain in left knee", "Musculoskeletal"),
    ("M17.11", "Osteoarthritis, right knee", "Musculoskeletal"),
    ("M17.12", "Osteoarthritis, left knee", "Musculoskeletal"),
    ("M23.221", "Old meniscus tear, right knee", "Musculoskeletal"),
    ("M23.222", "Old meniscus tear, left knee", "Musculoskeletal"),
    ("C50.911", "Breast cancer, right breast", "Oncology"),
    ("C34.90", "Lung cancer, unspecified side", "Oncology"),
    ("Z51.11", "Encounter for chemotherapy", "Oncology"),
]

DENIALS = [
    ("D01", "Member not eligible on date of service"),
    ("D02", "Duplicate of a claim already processed"),
    ("D03", "Timely filing limit exceeded (received more than 365 days after service)"),
    ("D04", "Prior authorization required and not on file"),
    ("D05", "Service not covered by the plan"),
    ("D06", "Missing or invalid claim information"),
    ("D07", "Bundled into another service on the same claim"),
    ("D08", "Out-of-network services not covered by this plan"),
]

POS = [
    ("10", "Telehealth in patient's home"),
    ("11", "Office"),
    ("21", "Inpatient hospital"),
    ("22", "Outpatient hospital"),
    ("23", "Emergency room - hospital"),
    ("24", "Ambulatory surgical center"),
    ("81", "Independent laboratory"),
]

STATUSES = [
    ("P", "Paid (finalized)"),
    ("D", "Denied (finalized, nothing paid)"),
    ("H", "Pended - received but not finalized yet"),
    ("X", "Reversed - replaced by an adjustment claim"),
    ("A", "Adjustment - replacement for a reversed claim (see original_claim_id)"),
]

PLANS = {
    "PPO500":   dict(name="PPO 500",            type="PPO",  ded=500,  oop=3000, coins=0.20, oon=True,  oon_coins=0.40, pcp=25, spec=50, er=250),
    "PPO1500":  dict(name="PPO 1500",           type="PPO",  ded=1500, oop=5000, coins=0.20, oon=True,  oon_coins=0.50, pcp=30, spec=60, er=300),
    "HDHP3300": dict(name="HDHP 3300 with HSA", type="HDHP", ded=3300, oop=6500, coins=0.10, oon=True,  oon_coins=0.40, pcp=0,  spec=0,  er=0),
    "EPO1000":  dict(name="EPO 1000",           type="EPO",  ded=1000, oop=4000, coins=0.20, oon=False, oon_coins=None, pcp=20, spec=40, er=200),
}

ZIP3 = {
    "WI": ["530", "531", "532", "534", "535", "537", "538", "539", "541", "542", "543", "544", "545", "546", "547", "548", "549"],
    "MN": ["550", "551", "553", "554", "556", "557", "559", "560", "561", "562", "563", "564", "565", "566"],
    "IL": ["600", "601", "602", "603", "604", "605", "606", "610", "611", "612", "613", "614", "615", "616", "617", "618", "619", "620", "622", "623", "624", "625", "626", "627"],
    "MI": ["480", "481", "482", "483", "484", "485", "486", "487", "488", "489", "490", "491", "492", "493", "494", "495", "496", "497", "498", "499"],
    "IA": ["500", "501", "502", "503", "504", "505", "506", "507", "508", "510", "511", "512", "513", "514", "515", "516", "520", "521", "522", "523", "524", "525", "526", "527", "528"],
    "FL": ["320", "321", "322", "323", "324", "325", "326", "327", "328", "329", "330", "331", "332", "333", "334", "335", "336", "337", "338", "339", "341", "342", "344", "346", "347", "349"],
    "TX": ["750", "751", "752", "754", "755", "756", "757", "758", "759", "760", "761", "762", "763", "764", "765", "766", "767", "768", "769", "770", "773", "774", "775", "776", "777", "778", "779", "780", "781", "782", "783", "784", "785", "786", "787", "788", "789", "790", "791", "792", "793", "794", "795", "796", "797", "798", "799"],
    "MA": ["010", "011", "012", "013", "014", "015", "016", "017", "018", "019", "020", "021", "022", "023", "024", "025", "026", "027"],
    "NJ": ["070", "071", "072", "073", "074", "075", "076", "077", "078", "079", "080", "081", "082", "083", "084", "085", "086", "087", "088", "089"],
    "CT": ["060", "061", "062", "063", "064", "065", "066", "067", "068", "069"],
}
LEADING_ZERO_STATES = {"MA", "NJ", "CT"}


def rzip(state):
    return R.choice(ZIP3[state]) + f"{R.randint(0, 99):02d}"


GROUPS_SPEC = [
    ("Northwoods Paper Company", "Manufacturing", "WI"),
    ("Fox Valley Dairy Cooperative", "Agriculture", "WI"),
    ("Lakeshore Tool & Die", "Manufacturing", "WI"),
    ("Cedar Creek Credit Union", "Financial Services", "WI"),
    ("Pinery Logistics", "Transportation", "WI"),
    ("Central Sands Potato Growers", "Agriculture", "WI"),
    ("Red Pine Senior Living", "Healthcare", "WI"),
    ("Moraine Electric Supply", "Wholesale", "WI"),
    ("Kettle Hills Brewing", "Food & Beverage", "WI"),
    ("Wolf River Hardwoods", "Manufacturing", "WI"),
    ("North Star Precision Plastics", "Manufacturing", "MN"),
    ("Lake Country Grocers", "Retail", "MN"),
    ("Boundary Waters Outfitters", "Retail", "MN"),
    ("Prairie State Insurance Agency", "Financial Services", "IL"),
    ("Lincolnway Freight", "Transportation", "IL"),
    ("Calumet Steel Fabricators", "Manufacturing", "IL"),
    ("Great Lakes Marine Service", "Marine", "MI"),
    ("Thumb Area Orchards", "Agriculture", "MI"),
    ("Hawkeye Seed & Feed", "Agriculture", "IA"),
    ("Cedar River Software", "Technology", "IA"),
    ("Gulf Breeze Hospitality", "Hospitality", "FL"),
    ("Suncoast Pool & Spa", "Construction", "FL"),
    ("Mangrove Bay Marina", "Marine", "FL"),
    ("Lone Prairie Energy Services", "Energy", "TX"),
    ("Brazos Valley Builders", "Construction", "TX"),
    ("Hill Country Veterinary Group", "Healthcare", "TX"),
    ("Cape Ann Seafood Processors", "Food & Beverage", "MA"),
    ("Merrimack Valley Machine Works", "Manufacturing", "MA"),
    ("Pine Barrens Landscaping", "Services", "NJ"),
    ("Housatonic Dental Partners", "Healthcare", "CT"),
]

FIRST_M = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
           "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua",
           "Kenneth", "Kevin", "Brian", "George", "Timothy", "Ronald", "Jason", "Edward", "Jeffrey", "Ryan",
           "Jacob", "Gary", "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin", "Scott", "Brandon",
           "Benjamin", "Samuel", "Gregory", "Alexander", "Patrick", "Frank", "Raymond", "Jack", "Dennis", "Jerry",
           "Tyler", "Aaron", "Jose", "Adam", "Nathan", "Henry", "Zachary", "Douglas", "Peter", "Kyle",
           "Noah", "Ethan", "Jeremy", "Walter", "Christian", "Keith", "Roger", "Terry", "Austin", "Sean",
           "Gerald", "Carl", "Harold", "Dylan", "Arthur", "Lawrence", "Jordan", "Jesse", "Bryan", "Billy",
           "Liam", "Mason", "Logan", "Owen", "Wyatt", "Carter", "Hunter", "Caleb", "Luke", "Isaac"]
FIRST_F = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen",
           "Lisa", "Nancy", "Betty", "Sandra", "Margaret", "Ashley", "Kimberly", "Emily", "Donna", "Michelle",
           "Carol", "Amanda", "Melissa", "Deborah", "Stephanie", "Dorothy", "Rebecca", "Sharon", "Laura", "Cynthia",
           "Amy", "Kathleen", "Angela", "Shirley", "Brenda", "Emma", "Anna", "Pamela", "Nicole", "Samantha",
           "Katherine", "Christine", "Helen", "Debra", "Rachel", "Carolyn", "Janet", "Maria", "Catherine", "Heather",
           "Diane", "Olivia", "Julie", "Joyce", "Victoria", "Ruth", "Virginia", "Lauren", "Kelly", "Christina",
           "Joan", "Evelyn", "Judith", "Andrea", "Hannah", "Megan", "Cheryl", "Jacqueline", "Martha", "Madison",
           "Teresa", "Gloria", "Sara", "Janice", "Ann", "Kathryn", "Abigail", "Sophia", "Frances", "Jean",
           "Ava", "Isabella", "Mia", "Harper", "Ella", "Chloe", "Grace", "Lily", "Zoe", "Nora"]
LAST = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
        "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
        "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
        "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
        "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts",
        "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Reyes",
        "Stewart", "Morris", "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper",
        "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
        "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes",
        "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long", "Ross", "Foster", "Jimenez",
        "Schmidt", "Mueller", "Schultz", "Wagner", "Becker", "Hoffmann", "Krueger", "Zimmerman", "Olson", "Larson",
        "Johnsen", "Hanson", "Nowak", "Kowalski", "Wisniewski", "Lindgren", "Bauer", "Fischer", "Weber", "Koch",
        "Novak", "Jensen", "Carlson", "Erickson", "Lund", "Berg", "Halvorson", "Dahl", "Brandt", "Vogel"]

FAC_PREFIX = ["Northwoods", "Lakeview", "Riverbend", "Prairie", "Cedar Valley", "Pine Ridge", "Harbor", "Summit",
              "Meadowbrook", "Bayside", "Oak Hollow", "Granite", "Clearwater", "Sandstone", "Willow Creek",
              "Bluestem", "Heartland", "Crescent", "Silverleaf", "Stonebridge", "Maple Grove", "Ironwood",
              "Juniper", "Seaside", "Highland", "Valley View", "Brookside", "Fairhaven", "Westfield", "Eastgate",
              "Red Cedar", "Timberline", "Goldenrod", "Driftwood", "Hollister", "Kingsley", "Larkspur", "Mistral"]


# --------------------------------------------------------------------------- providers

def npi_check_digit(nine):
    s = "80840" + nine
    total, dbl = 0, True
    for ch in reversed(s):
        n = int(ch)
        if dbl:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        dbl = not dbl
    return str((10 - total % 10) % 10)


USED_NPI = set()


def new_npi(first="1"):
    while True:
        nine = first + "".join(str(R.randint(0, 9)) for _ in range(8))
        npi = nine + npi_check_digit(nine)
        if npi not in USED_NPI:
            USED_NPI.add(npi)
            return npi


PROVIDERS = []
PROV = {}
POOL = defaultdict(list)          # (state, specialty) -> [provider ids]
_pseq = [0]
_fac_names = set()


def add_provider(ptype, specialty, state, name, network, contract_pct=None, mult=None):
    _pseq[0] += 1
    pid = f"P{_pseq[0]:06d}"
    p = dict(provider_id=pid, npi=new_npi("1" if ptype == "INDIVIDUAL" else R.choice("12")),
             provider_name=name, provider_type=ptype, specialty=specialty,
             address_state=state, address_zip=rzip(state), network_status=network,
             contract_pct_of_billed=contract_pct,
             mult=mult if mult else ((R.uniform(0.9, 1.3) if R.random() < 0.06 else R.uniform(1.5, 2.8)) if ptype == "INDIVIDUAL" else R.uniform(1.8, 3.0)),
             fmult=R.uniform(5.0, 9.0))
    PROVIDERS.append(p)
    PROV[pid] = p
    POOL[(state, specialty)].append(pid)
    return pid


def fac_name(suffixes):
    for _ in range(500):
        n = f"{R.choice(FAC_PREFIX)} {R.choice(suffixes)}"
        if n not in _fac_names:
            _fac_names.add(n)
            return n
    raise RuntimeError("ran out of facility names")


IND_SPECS = {  # specialty: (count per 1000 members, credential choices)
    "Family Medicine": (6.5, ["MD", "MD", "MD", "DO"]),
    "Internal Medicine": (4.0, ["MD", "MD", "DO"]),
    "Pediatrics": (3.0, ["MD", "MD", "DO"]),
    "Obstetrics & Gynecology": (1.6, ["MD", "MD", "DO"]),
    "Cardiology": (1.3, ["MD"]),
    "Orthopedic Surgery": (1.3, ["MD", "DO"]),
    "Physical Therapy": (2.3, ["PT, DPT"]),
    "Behavioral Health": (3.6, ["PhD", "LCSW", "LCSW", "LPC", "PsyD"]),
    "Psychiatry": (0.8, ["MD", "DO"]),
    "Emergency Medicine": (2.6, ["MD", "DO"]),
    "Hospitalist": (2.0, ["MD", "DO"]),
    "General Surgery": (1.0, ["MD"]),
    "Radiology": (1.6, ["MD"]),
    "Oncology": (0.8, ["MD"]),
    "Gastroenterology": (1.0, ["MD"]),
}
PCP_SPECS = {"Family Medicine", "Internal Medicine", "Pediatrics"}
COPAY_PCP_CODES = {"99202", "99203", "99204", "99205", "99211", "99212", "99213", "99214", "99215", "90791", "90834", "90837"}
COPAY_SPEC_CODES = {"97161"}
EM_CODES = {"99202", "99203", "99204", "99205", "99211", "99212", "99213", "99214", "99215"}


def build_providers(members_by_state):
    for state, n in sorted(members_by_state.items()):
        k = n / 1000.0
        for spec, (rate, creds) in IND_SPECS.items():
            cnt = max(1, int(round(rate * k)))
            for _ in range(cnt):
                female = R.random() < 0.5
                fn = R.choice(FIRST_F if female else FIRST_M)
                name = f"{fn} {R.choice(LAST)}, {R.choice(creds)}"
                net = "INN" if R.random() < 0.90 else "OON"
                add_provider("INDIVIDUAL", spec, state, name, net)
        for _ in range(max(1, int(round(n / 650)))):
            net = "INN" if R.random() < 0.92 else "OON"
            add_provider("FACILITY", "Acute Care Hospital", state,
                         fac_name(["Regional Medical Center", "Memorial Hospital", "Community Hospital", "General Hospital"]),
                         net, money(R.uniform(0.42, 0.62)) if net == "INN" else None)
        for _ in range(max(1, int(round(n / 1100)))):
            add_provider("FACILITY", "Ambulatory Surgery Center", state,
                         fac_name(["Surgery Center", "Outpatient Surgery Center", "Surgical Suites"]),
                         "INN", money(R.uniform(0.45, 0.65)))
        for _ in range(max(1, int(round(n / 900)))):
            net = "INN" if R.random() < 0.85 else "OON"
            add_provider("FACILITY", "Imaging Center", state,
                         fac_name(["Imaging Center", "Advanced Imaging", "Diagnostic Imaging"]), net)
    add_provider("FACILITY", "Acute Care Hospital", "WI",
                 fac_name(["Regional Medical Center", "Memorial Hospital", "Community Hospital"]), "OON")
    add_provider("FACILITY", "Ambulatory Surgery Center", "IL", fac_name(["Surgery Center", "Surgical Suites"]), "OON")
    # independent labs serve everybody
    for st in ["NJ", "IL", "TX"]:
        add_provider("FACILITY", "Independent Laboratory", st, fac_name(["Diagnostic Laboratories", "Clinical Labs"]), "INN")
    add_provider("FACILITY", "Independent Laboratory", "WI", fac_name(["Reference Laboratory"]), "OON")


def pick(state, spec):
    pool = POOL.get((state, spec))
    if not pool:
        # fall back to any state that has the specialty
        pool = [pid for (s, sp), ids in POOL.items() if sp == spec for pid in ids]
    return R.choice(pool)


def pick_hospital(state):
    pool = POOL.get((state, "Acute Care Hospital")) or []
    inn = [h for h in pool if PROV[h]["network_status"] == "INN"]
    if inn and R.random() < 0.93:
        return R.choice(inn)
    return R.choice(pool) if pool else pick(state, "Acute Care Hospital")


def pick_lab():
    labs = [pid for (s, sp), ids in POOL.items() if sp == "Independent Laboratory" for pid in ids]
    inn = [l for l in labs if PROV[l]["network_status"] == "INN"]
    oon = [l for l in labs if PROV[l]["network_status"] == "OON"]
    return R.choice(oon) if (oon and R.random() < 0.06) else R.choice(inn)


# --------------------------------------------------------------------------- members & eligibility

MEMBERS = []
MEM = {}
SPANS = []          # eligibility rows (dicts)
MEM_SPANS = defaultdict(list)
_mseq = [0]


def new_member(sub_id, rel, first, last, dob, gender, state, zipc):
    _mseq[0] += 1
    mid = f"M{_mseq[0]:07d}"
    m = dict(member_id=mid, subscriber_id=sub_id or mid, relationship_code=rel, first_name=first, last_name=last,
             birth_date=dob, gender=gender, address_state=state, address_zip=zipc)
    MEMBERS.append(m)
    MEM[mid] = m
    return m


def add_span(mid, gid, plan, tier, eff, term):
    row = dict(member_id=mid, group_id=gid, plan_code=plan, coverage_tier=tier, effective_date=eff, term_date=term)
    SPANS.append(row)
    MEM_SPANS[mid].append(row)
    return row


def dob_for_age(age, ref=date(2026, 1, 1)):
    return date(ref.year - age, 1, 1) - timedelta(days=R.randint(0, 364))


GROUPS = []
FAMILIES = []   # dicts: members, spans (list of (eff, term, plan)), group, mother (member id) etc.
NEWBORN_EVENTS = []  # (mother_id, baby_id, birth_date)


def build_groups_and_members():
    plan_sets = [["PPO500"], ["PPO1500"], ["HDHP3300"], ["EPO1000"], ["PPO500", "HDHP3300"],
                 ["PPO1500", "HDHP3300"], ["EPO1000", "HDHP3300"], ["PPO500", "PPO1500"]]
    for i, (name, ind, st) in enumerate(GROUPS_SPEC):
        gid = f"G{1001 + i}"
        eff = first_of_month(rdate(d(2014, 1, 1), d(2024, 6, 1)))
        term = None
        if i == 12:
            eff = d(2025, 7, 1)            # new client mid-2025
        if i == 25:
            eff = d(2026, 1, 1)            # new client 2026
        if i == 18:
            term = d(2025, 12, 31)         # left at end of 2025
        if i == 22:
            term = d(2026, 6, 30)          # left mid-2026
        plans = R.choice(plan_sets)
        if i == 0:
            plans = ["PPO500"]             # moves to HDHP on 2026-01-01
        n_subs = R.randint(25, 150) if st != "WI" else R.randint(80, 230)
        GROUPS.append(dict(group_id=gid, group_name=name, industry=ind, state=st, effective_date=eff,
                           term_date=term, plans=plans, n_subs=n_subs, plan_change=(i == 0)))

    for g in GROUPS:
        for _ in range(g["n_subs"]):
            make_family(g)
    # dependents whose coverage never overlapped their life (born after the family left, or aged out before it joined)
    # are dropped, except two kept as a data problem
    no_cov = [m for m in MEMBERS if not MEM_SPANS[m["member_id"]]]
    keep = set(m["member_id"] for m in R.sample(no_cov, min(2, len(no_cov))))
    MEMBERS[:] = [m for m in MEMBERS if MEM_SPANS[m["member_id"]] or m["member_id"] in keep]


def make_family(g):
    st = g["state"]
    sub_age = wchoice([(R.randint(21, 29), 20), (R.randint(30, 39), 26), (R.randint(40, 49), 24),
                       (R.randint(50, 59), 21), (R.randint(60, 66), 9)])
    sub_gender = R.choice("MF")
    last = R.choice(LAST)
    zipc = rzip(st)
    sub = new_member(None, "SUB", R.choice(FIRST_M if sub_gender == "M" else FIRST_F), last,
                     dob_for_age(sub_age), sub_gender, st, zipc)
    members = [sub]
    spouse = None
    if sub_age >= 24 and R.random() < 0.55:
        sg = ("F" if sub_gender == "M" else "M") if R.random() < 0.95 else sub_gender
        sp_age = max(21, min(70, sub_age + R.randint(-6, 6)))
        spouse = new_member(sub["member_id"], "SPS", R.choice(FIRST_M if sg == "M" else FIRST_F),
                            last if R.random() < 0.8 else R.choice(LAST), dob_for_age(sp_age), sg, st, zipc)
        members.append(spouse)
    kids = []
    if 24 <= sub_age <= 58:
        nk = wchoice([(0, 35), (1, 25), (2, 25), (3, 12), (4, 3)])
        for _ in range(nk):
            ka = R.randint(max(1, sub_age - 44), max(1, min(25, sub_age - 20)))
            kg = R.choice("MF")
            kid = new_member(sub["member_id"], "DEP", R.choice(FIRST_M if kg == "M" else FIRST_F), last,
                             dob_for_age(ka), kg, st, zipc)
            kids.append(kid)
            members.append(kid)

    # coverage periods for the family
    if R.random() < 0.80:
        start = first_of_month(rdate(d(2012, 1, 1), d(2024, 12, 1)))
    else:
        start = first_of_month(rdate(d(2025, 1, 1), d(2026, 9, 1)))
    start = max(start, g["effective_date"])
    if g["term_date"] and start > g["term_date"] - timedelta(days=60):
        start = max(first_of_month(rdate(d(2012, 1, 1), d(2024, 12, 1))), g["effective_date"])
    periods = []
    term = g["term_date"]
    if R.random() < 0.17:
        t = month_end(rdate(start + timedelta(days=90), d(2026, 9, 15)))
        if t > start and (term is None or t < term):
            term = t
    periods.append([start, term])
    if term and not g["term_date"] and term < d(2026, 3, 1) and R.random() < 0.2:
        rs = first_of_month(term + timedelta(days=R.randint(60, 240)))
        if rs <= d(2026, 9, 1):
            periods.append([rs, None])

    has_sp = spouse is not None
    tier = {(False, False): "EE", (True, False): "ES", (False, True): "EC", (True, True): "FAM"}

    # newborn?
    mother = sub if sub_gender == "F" else (spouse if spouse and spouse["gender"] == "F" else None)
    baby = None
    if mother is not None and 22 <= age_on(mother["birth_date"], d(2026, 1, 1)) <= 41 and R.random() < 0.10:
        cands = []
        for a, b in periods:
            lo = max(a + timedelta(days=200), d(2025, 2, 1))
            hi = min(b or d(2026, 8, 31), d(2026, 8, 31))
            if lo <= hi:
                cands.append((lo, hi))
        if cands:
            lo, hi = R.choice(cands)
            bd = rdate(lo, hi)
            kg = R.choice("MF")
            baby = new_member(sub["member_id"], "DEP", R.choice(FIRST_M if kg == "M" else FIRST_F), last,
                              bd, kg, st, zipc)
            members.append(baby)
            kids.append(baby)
            NEWBORN_EVENTS.append((mother["member_id"], baby["member_id"], bd))
    t = tier[(has_sp, bool(kids))]
    plan = R.choice(g["plans"])

    for m in members:
        for a, b in periods:
            eff, end = a, b
            if m["relationship_code"] == "DEP":
                if m["birth_date"] > (b or OPEN_END):
                    continue
                eff = max(a, m["birth_date"])
                b26 = date(m["birth_date"].year + 26, m["birth_date"].month, min(m["birth_date"].day, 28))
                age_out = month_end(b26)
                if age_out < eff:
                    continue
                if end is None or age_out < end:
                    end = age_out
            if g["plan_change"] and eff < d(2026, 1, 1) and (end is None or end >= d(2026, 1, 1)):
                add_span(m["member_id"], g["group_id"], "PPO500", t, eff, d(2025, 12, 31))
                add_span(m["member_id"], g["group_id"], "HDHP3300", t, d(2026, 1, 1), end)
            elif g["plan_change"] and eff >= d(2026, 1, 1):
                add_span(m["member_id"], g["group_id"], "HDHP3300", t, eff, end)
            else:
                add_span(m["member_id"], g["group_id"], plan, t, eff, end)
    FAMILIES.append(dict(members=members, group=g))


def span_for(mid, dt_):
    for s in MEM_SPANS.get(mid, []):
        if s.get("bogus"):
            continue
        if s["effective_date"] <= dt_ <= (s["term_date"] or OPEN_END):
            return s
    return None


def covered_intervals(mid):
    iv = []
    for s in sorted(MEM_SPANS[mid], key=lambda x: x["effective_date"]):
        a, b = s["effective_date"], s["term_date"] or OPEN_END
        if iv and a <= iv[-1][1] + timedelta(days=1):
            iv[-1][1] = max(iv[-1][1], b)
        else:
            iv.append([a, b])
    out = []
    for a, b in iv:
        a2, b2 = max(a, SVC_START), min(b, SVC_END)
        if a2 <= b2:
            out.append((a2, b2))
    return out


# --------------------------------------------------------------------------- claim builders

CLAIMS = []


def prof_claim(mid, prov, pos, dx, lines, flags=()):
    """lines: (date, code, units, modifier)."""
    p = PROV[prov]
    out = []
    for dt_, code, units, mod in lines:
        per = FEES[code] * p["mult"] * (0.32 if mod == "26" else 1.0)
        out.append(dict(date=dt_, code=code, rev=None, mod=mod, units=units, billed=float(max(1, round(per * units)))))
    rend = prov if p["provider_type"] == "INDIVIDUAL" else None
    c = dict(ctype="PROF", member=mid, billing=prov, rendering=rend, pos=pos, bill_type=None,
             admit=None, discharge=None, frm=min(l["date"] for l in out), to=max(l["date"] for l in out),
             dx=list(dx)[:4], lines=out, flags=set(flags))
    CLAIMS.append(c)
    return c


REV_CHARGE = {"0260": (500, 1500), "0120": (5500, 9000), "0170": (1800, 3200), "0200": (9000, 14000), "0250": (900, 3200),
              "0270": (400, 4000), "0300": (700, 2800), "0320": (300, 1200), "0350": (1500, 4000),
              "0360": (9000, 22000), "0410": (900, 3200), "0480": (1500, 3500), "0490": (3000, 8000),
              "0610": (2000, 4500), "0636": (100, 900), "0710": (1200, 3500), "0720": (4000, 9000),
              "0730": (200, 600)}
PER_DAY_REVS = {"0120", "0170", "0200"}
ER_FAC_CHARGE = {"99283": (1800, 3200), "99284": (3200, 5200), "99285": (5200, 8500)}


def inst_claim(mid, fac, bill_type, dx, lines, admit=None, discharge=None, flags=()):
    """lines: (date, rev, code_or_None, units[, scale]). scale multiplies the charge (e.g. length of stay)."""
    p = PROV[fac]
    out = []
    for ln in lines:
        dt_, rev, code, units = ln[:4]
        scale = ln[4] if len(ln) > 4 else 1
        if rev == "0450" and code in ER_FAC_CHARGE:
            billed = round(R.uniform(*ER_FAC_CHARGE[code]))
        elif code and code.startswith("J"):
            billed = max(1, round(FEES[code] * R.uniform(2.5, 3.5) * units))
        elif code and code in FEES and rev not in PER_DAY_REVS:
            billed = max(1, round(FEES[code] * p["fmult"] * units))
        else:
            lo, hi = REV_CHARGE[rev]
            billed = round(R.uniform(lo, hi)) * (units if rev in PER_DAY_REVS else 1) * scale
        out.append(dict(date=dt_, code=code, rev=rev, mod=None, units=units, billed=float(billed)))
    frm = admit or min(l["date"] for l in out)
    to = discharge or max(l["date"] for l in out)
    c = dict(ctype="INST", member=mid, billing=fac, rendering=None, pos=None, bill_type=bill_type,
             admit=admit, discharge=discharge, frm=frm, to=to, dx=list(dx)[:4], lines=out, flags=set(flags))
    CLAIMS.append(c)
    return c


class Person:
    def __init__(self, m):
        self.m = m
        self.id = m["member_id"]
        self.state = m["address_state"]
        self.gender = m["gender"]
        self.dob = m["birth_date"]
        a = age_on(self.dob, d(2026, 1, 1))
        self.age26 = a
        if a < 18:
            self.pcp = pick(self.state, "Pediatrics" if R.random() < 0.6 else "Family Medicine")
        else:
            self.pcp = pick(self.state, "Family Medicine" if R.random() < 0.62 else "Internal Medicine")
        self.hospital = pick_hospital(self.state)
        self.colo_done = False
        r = R.random
        self.dm = a >= 30 and r() < (0.03 + max(0, a - 30) * 0.003)
        self.htn = a >= 28 and r() < (0.05 + max(0, a - 28) * 0.007)
        self.lipid = a >= 35 and r() < (0.06 + max(0, a - 35) * 0.005)
        self.thyroid = self.gender == "F" and a >= 25 and r() < 0.06
        self.asthma = r() < 0.05
        self.copd = a >= 50 and r() < 0.04
        self.cardiac = a >= 50 and r() < (0.03 + (a - 50) * 0.006)
        self.bh = 10 <= a <= 64 and r() < 0.14
        self.onc = (a >= 40 and r() < 0.009) or (25 <= a < 40 and r() < 0.002)
        self.chronic_dx = [x for x, flag in (("E11.9" if R.random() < 0.7 else "E11.65", self.dm), ("I10", self.htn),
                                             ("E78.5", self.lipid), ("E03.9", self.thyroid), ("J44.9", self.copd),
                                             ("J45.909", self.asthma)) if flag]

    def age(self, on):
        return age_on(self.dob, on)


def em_level(kind):
    if kind == "acute":
        return wchoice([("99212", 30), ("99213", 55), ("99214", 15)])
    if kind == "chronic":
        return wchoice([("99213", 40), ("99214", 50), ("99215", 10)])
    if kind == "new_spec":
        return wchoice([("99203", 45), ("99204", 45), ("99205", 10)])
    return wchoice([("99213", 50), ("99214", 50)])


def lab_claim(p, dt_, codes, dx):
    if R.random() < 0.2:
        lines = [(dt_, "0300", "36415", 1)] + [(dt_, "0300", c, 1) for c in codes]
        return inst_claim(p.id, p.hospital, "0131", dx, lines)
    lines = [(dt_, "36415", 1, None)] + [(dt_, c, 1, None) for c in codes]
    return prof_claim(p.id, pick_lab(), "81", dx, lines)


def imaging(p, dt_, code, dx, mod=None, flags=()):
    if R.random() < 0.5:
        prof_claim(p.id, pick(p.state, "Imaging Center"), "11", dx, [(dt_, code, 1, mod)], flags)
    else:
        rev = {"72148": "0610", "73721": "0610", "70450": "0350", "74177": "0350", "93306": "0480"}.get(code, "0320")
        inst_claim(p.id, p.hospital, "0131", dx, [(dt_, rev, code, 1)], flags=flags)
        prof_claim(p.id, pick(p.state, "Radiology"), "22", dx, [(dt_, code, 1, "26")], flags)


def office_visit(p, dt_, kind, dx, extra=(), prov=None, tele=False, flags=()):
    prov = prov or p.pcp
    code = em_level(kind)
    pos, mod = ("10", "95") if tele else ("11", None)
    lines = [(dt_, code, 1, mod)] + [(dt_, c, u, m) for c, u, m in extra]
    return prof_claim(p.id, prov, pos, dx, lines, flags)


def acute_visit(p, dt_, flags=()):
    a = p.age(dt_)
    if a < 12:
        sc = wchoice([("J06.9", 30), ("H66.90", 22), ("J02.0", 10), ("J02.9", 8), ("J11.1", 8), ("H10.9", 10), ("R05.9", 12)])
    else:
        sc = wchoice([("J06.9", 22), ("J02.0", 7), ("J02.9", 6), ("J11.1", 7), ("U07.1", 5), ("N39.0", 8), ("L03.90", 4),
                      ("R51.9", 5), ("G43.909", 3), ("S93.401A", 5), ("K21.9", 6), ("R10.9", 5), ("R05.9", 8),
                      ("H10.9", 4), ("E66.9", 2), ("R73.03", 3)])
    if sc in ("J11.1", "U07.1") and 4 <= dt_.month <= 9 and R.random() < 0.85:
        sc = "J06.9" if R.random() < 0.6 else "R05.9"
    extra = []
    if sc in ("J02.0", "J02.9") and R.random() < 0.8:
        extra.append(("87880", 1, None))
    if sc == "J11.1" and R.random() < 0.8:
        extra.append(("87804", 1, None))
    if sc == "U07.1" and R.random() < 0.6:
        extra.append(("87635", 1, None))
    if sc == "N39.0":
        extra.append(("81002", 1, None))
    tele = a >= 18 and sc in ("J06.9", "U07.1", "R05.9", "K21.9", "H10.9") and R.random() < 0.25
    if tele:
        extra = []
    c = office_visit(p, dt_, "acute", [sc], extra, tele=tele, flags=flags)
    if sc == "S93.401A" and R.random() < 0.6 and "post_term" not in flags:
        imaging(p, dt_, "73610", [sc], "RT")
    return c


def preventive_visit(p, dt_):
    a = p.age(dt_)
    code = ("99391" if a < 1 else "99392" if a < 5 else "99393" if a < 12 else "99394" if a < 18 else
            "99395" if a < 40 else "99396" if a < 65 else "99397")
    if a < 18:
        dx = ["Z00.129"]
    else:
        dx = ["Z00.01" if p.chronic_dx and R.random() < 0.5 else "Z00.00"] + p.chronic_dx[:3]
    prof_claim(p.id, p.pcp, "11", dx, [(dt_, code, 1, None)])
    if a >= 18 and R.random() < 0.8:
        codes = ["80053", "80061", "85025"]
        if p.dm:
            codes.append("83036")
        if p.thyroid:
            codes.append("84443")
        lab_claim(p, dt_, codes, dx[:1] + p.chronic_dx[:3])


def chronic_visit(p, dt_):
    dx = p.chronic_dx[:4]
    extra = []
    if p.dm and R.random() < 0.5:
        extra.append(("83036", 1, None))       # point-of-care A1c in the office
    office_visit(p, dt_, "chronic", dx, extra)
    codes = []
    if p.dm:
        codes += ["80053"] + ([] if extra else ["83036"])
    if p.htn and "80053" not in codes and R.random() < 0.5:
        codes.append("80053")
    if p.lipid and R.random() < 0.35:
        codes.append("80061")
    if p.thyroid and R.random() < 0.5:
        codes.append("84443")
    if codes:
        lab_claim(p, dt_, codes, dx)


def cardiac_visit(p, dt_):
    dx = [wchoice([("I25.10", 50), ("I48.91", 35), ("I50.9", 15)])] + [x for x in p.chronic_dx if x in ("I10", "E78.5")]
    prov = pick(p.state, "Cardiology")
    extra = [("93000", 1, None)] if R.random() < 0.6 else []
    office_visit(p, dt_, "chronic", dx, extra, prov=prov)
    if R.random() < 0.15:
        imaging(p, dt_ + timedelta(days=R.randint(3, 20)), "93306", dx)


def er_visit(p, dt_):
    a = p.age(dt_)
    if a < 12:
        sc = wchoice([("H66.90", 30), ("J06.9", 25), ("J45.909", 15), ("S93.401A", 15), ("R10.9", 15)])
    else:
        sc = wchoice([("R07.9", 22), ("R10.9", 20), ("S93.401A", 12), ("R51.9", 10), ("L03.90", 8),
                      ("J18.9", 8), ("N39.0", 8), ("J45.909", 6), ("G43.909", 6)])
    if sc == "J18.9" and 4 <= dt_.month <= 9 and R.random() < 0.6:
        sc = "R10.9"
    admit = sc in ("R07.9", "J18.9") and a >= 40 and R.random() < 0.18
    if admit:
        dx = {"R07.9": ["I25.10", "R07.9", "I10"], "J18.9": ["J18.9", "J44.9"]}[sc]
        inpatient(p, dt_, dx, R.randint(2, 5), via_er=True)
        return
    level = wchoice([("99283", 35), ("99284", 45), ("99285", 20)])
    lines = [(dt_, "0450", level, 1)]
    if sc in ("R07.9", "R10.9", "J18.9", "L03.90", "N39.0") or R.random() < 0.3:
        lines += [(dt_, "0300", "80053", 1), (dt_, "0300", "85025", 1)]
    if sc in ("R07.9", "J18.9"):
        lines.append((dt_, "0320", "71046", 1))
    if sc == "R07.9":
        lines.append((dt_, "0730", "93000", 1))
    if sc == "R10.9" and R.random() < 0.6:
        lines.append((dt_, "0350", "74177", 1))
    if sc in ("R51.9", "G43.909") and R.random() < 0.5:
        lines.append((dt_, "0350", "70450", 1))
    if sc == "S93.401A":
        lines.append((dt_, "0320", "73610", 1))
    if sc in ("L03.90", "N39.0", "J18.9"):
        lines.append((dt_, "0636", "J0696", 4))
    if sc in ("J45.909", "G43.909", "R51.9") and R.random() < 0.6:
        lines.append((dt_, "0636", "J1100", 10))
    if R.random() < 0.5:
        lines.append((dt_, "0250", None, 1))
    dx = [sc] + ([x for x in p.chronic_dx if x != sc][:2])
    inst_claim(p.id, p.hospital, "0131", dx, lines, flags=("emergency", "er_facility"))
    prof_claim(p.id, pick(PROV[p.hospital]["address_state"], "Emergency Medicine"), "23", dx,
               [(dt_, level, 1, None)], flags=("emergency",))
    if sc == "R10.9" and a >= 25 and R.random() < 0.25:
        gallbladder_surgery(p, dt_ + timedelta(days=R.randint(14, 45)))


def inpatient(p, admit, dx, los, via_er=False, flags=()):
    disch = admit + timedelta(days=los)
    lines = []
    if via_er:
        lines.append((admit, "0450", "99285", 1))
    icu = min(los - 1, R.randint(1, 2)) if (R.random() < 0.15 and los > 1) else 0
    if icu:
        lines.append((admit, "0200", None, icu))
    lines += [(admit, "0120", None, los - icu), (admit, "0250", None, 1, los), (admit, "0300", None, 1, los),
              (admit, "0270", None, 1)]
    if dx[0] in ("J18.9", "J44.9", "I50.9"):
        lines.append((admit, "0410", None, 1, los))
    if R.random() < 0.6:
        lines.append((admit, "0320", "71046", 1))
    if R.random() < 0.4:
        lines.append((admit, "0730", "93000", 1))
    fl = set(flags) | ({"emergency"} if via_er else {"pa_check"})
    inst_claim(p.id, p.hospital, "0111", dx, lines, admit=admit, discharge=disch, flags=fl)
    hosp = pick(PROV[p.hospital]["address_state"], "Hospitalist")
    pl = [(admit, "99223", 1, None)]
    for i in range(1, los):
        pl.append((admit + timedelta(days=i), "99232", 1, None))
    pl.append((disch, "99238", 1, None))
    prof_claim(p.id, hosp, "21", dx, pl, flags=("emergency",) if via_er else ())
    if via_er:
        prof_claim(p.id, pick(PROV[p.hospital]["address_state"], "Emergency Medicine"), "23", dx,
                   [(admit, "99285", 1, None)], flags=("emergency",))


def gallbladder_surgery(p, dt_):
    dx = ["K80.20"]
    office_visit(p, dt_ - timedelta(days=R.randint(5, 12)), "new_spec", dx, prov=pick(p.state, "General Surgery"))
    inst_claim(p.id, p.hospital, "0131", dx,
               [(dt_, "0360", "47562", 1), (dt_, "0710", None, 1), (dt_, "0250", None, 1), (dt_, "0270", None, 1),
                (dt_, "0300", "85025", 1)], flags=("pa_check",))
    prof_claim(p.id, pick(p.state, "General Surgery"), "22", dx, [(dt_, "47562", 1, None)])


def screening_colonoscopy(p, dt_):
    biopsy = R.random() < 0.35
    code = "45380" if biopsy else "45378"
    dx = ["Z12.11"] + (["K57.30"] if R.random() < 0.3 else [])
    asc = pick(p.state, "Ambulatory Surgery Center")
    inst_claim(p.id, asc, "0831", dx, [(dt_, "0490", code, 1), (dt_, "0250", None, 1), (dt_, "0270", None, 1)],
               flags=("screening",))
    prof_claim(p.id, pick(p.state, "Gastroenterology"), "24", dx, [(dt_, code, 1, None)], flags=("screening",))
    if biopsy:
        lab_claim(p, dt_ + timedelta(days=1), ["85025"], dx)


def back_episode(p, start, end):
    dx = ["M54.50"]
    office_visit(p, start, "acute", dx)
    if R.random() < 0.3:
        imaging(p, start, "72148", dx, flags=("pa_check",))
    if R.random() < 0.55:
        pt_series(p, start + timedelta(days=R.randint(5, 20)), end, dx)


def knee_episode(p, start, end):
    side = R.choice(["RT", "LT"])
    oa = p.age(start) >= 50 and R.random() < 0.6
    dx = [("M17.11" if side == "RT" else "M17.12") if oa else ("M25.561" if side == "RT" else "M25.562")]
    ortho = pick(p.state, "Orthopedic Surgery")
    office_visit(p, start, "acute", dx)
    imaging(p, start, "73562", dx, side)
    dt_ = start + timedelta(days=R.randint(10, 30))
    if dt_ > end:
        return
    extra = []
    if R.random() < 0.35:
        # knee injection with an E&M. Most offices add modifier 25; when they don't, the E&M gets bundled.
        em_mod = "25" if R.random() < 0.7 else None
        c = prof_claim(p.id, ortho, "11", dx, [(dt_, em_level("new_spec"), 1, em_mod), (dt_, "20610", 1, side)])
        if em_mod is None:
            c["lines"][0]["bundle_deny"] = True
    else:
        office_visit(p, dt_, "new_spec", dx, prov=ortho)
    if oa and p.age(start) >= 55 and R.random() < 0.12:
        sd = dt_ + timedelta(days=R.randint(30, 90))
        if sd <= end:
            los = R.randint(1, 3)
            disch = sd + timedelta(days=los)
            inst_claim(p.id, p.hospital, "0111", dx,
                       [(sd, "0120", None, los), (sd, "0360", "27447", 1), (sd, "0710", None, 1), (sd, "0250", None, 1, los),
                        (sd, "0270", None, 1, 3), (sd, "0300", None, 1)], admit=sd, discharge=disch, flags=("pa_check",))
            prof_claim(p.id, ortho, "21", dx, [(sd, "27447", 1, side)])
            pt_series(p, disch + timedelta(days=R.randint(3, 10)), end, dx)
        return
    if not oa and R.random() < 0.4:
        mdt = dt_ + timedelta(days=R.randint(3, 15))
        if mdt <= end:
            imaging(p, mdt, "73721", dx, side, flags=("pa_check",))
            if R.random() < 0.35:
                sd = mdt + timedelta(days=R.randint(14, 45))
                if sd <= end:
                    tdx = ["M23.221" if side == "RT" else "M23.222"]
                    asc = pick(p.state, "Ambulatory Surgery Center")
                    inst_claim(p.id, asc, "0831", tdx, [(sd, "0490", "29881", 1), (sd, "0250", None, 1), (sd, "0270", None, 1)],
                               flags=("pa_check",))
                    prof_claim(p.id, ortho, "24", tdx, [(sd, "29881", 1, side)])
                    pt_series(p, sd + timedelta(days=R.randint(5, 14)), end, tdx)


def pt_series(p, start, end, dx):
    pt = pick(p.state, "Physical Therapy")
    dt_ = start
    n = R.randint(6, 14)
    for i in range(n):
        if dt_ > end:
            break
        if i == 0:
            prof_claim(p.id, pt, "11", dx, [(dt_, "97161", 1, None), (dt_, "97110", 1, None)])
        else:
            prof_claim(p.id, pt, "11", dx, [(dt_, "97110", R.choice([1, 2, 2, 3]), None), (dt_, "97140", 1, None)])
        dt_ += timedelta(days=R.choice([3, 4, 7, 7]))


def bh_episode(p, start, end):
    dx = [wchoice([("F41.1", 45), ("F32.A", 40), ("F90.2", 15 if p.age(start) < 25 else 2)])]
    prov = pick(p.state, "Behavioral Health")
    tele = R.random() < 0.4
    dt_ = start
    n = R.randint(4, 26)
    for i in range(n):
        if dt_ > end:
            break
        code = "90791" if i == 0 else wchoice([("90834", 60), ("90837", 40)])
        t = tele and i > 0 and R.random() < 0.85
        prof_claim(p.id, prov, "10" if t else "11", dx, [(dt_, code, 1, "95" if t else None)])
        dt_ += timedelta(days=R.choice([7, 7, 14, 14, 21]))
    if R.random() < 0.3:
        psy = pick(p.state, "Psychiatry")
        dt_ = start + timedelta(days=R.randint(10, 40))
        for _ in range(R.randint(1, 4)):
            if dt_ > end:
                break
            office_visit(p, dt_, "chronic", dx, prov=psy, tele=R.random() < 0.3)
            dt_ += timedelta(days=R.randint(30, 90))


def chemo_course(p, start, end):
    dx = ["Z51.11", "C50.911" if p.gender == "F" and R.random() < 0.7 else "C34.90"]
    onc = pick(p.state, "Oncology")
    office_visit(p, start - timedelta(days=R.randint(7, 20)), "new_spec", dx[1:], prov=onc)
    dt_ = start
    hosp_infusion = R.random() < 0.5
    for _ in range(R.randint(4, 8)):
        if dt_ > end:
            break
        if hosp_infusion:
            inst_claim(p.id, p.hospital, "0131", dx, [(dt_, "0260", "96413", 1), (dt_, "0260", "96415", 1),
                                                       (dt_, "0636", "J9271", 200), (dt_, "0300", "85025", 1)])
            prof_claim(p.id, onc, "22", dx, [(dt_, "99214", 1, None)])
        else:
            prof_claim(p.id, onc, "11", dx, [(dt_, "99214", 1, "25"), (dt_, "96413", 1, None), (dt_, "96415", 1, None),
                                              (dt_, "J9271", 200, None), (dt_, "85025", 1, None)])
        dt_ += timedelta(days=21)


def maternity(mother, baby_id, bd):
    dx = ["Z34.90"]
    ob = pick(mother.state, "Obstetrics & Gynecology")
    for days_before, code in ((140, "76805"), (14, "59025")):
        dt_ = bd - timedelta(days=days_before)
        if span_for(mother.id, dt_) and dt_ >= SVC_START and (code == "76805" or R.random() < 0.5):
            prof_claim(mother.id, ob, "11", dx, [(dt_, code, 1, None)])
    if span_for(mother.id, bd - timedelta(days=200)) and bd - timedelta(days=200) >= SVC_START:
        lab_claim(mother, bd - timedelta(days=200), ["85025"], dx)
    los = R.randint(1, 3)
    inst_claim(mother.id, mother.hospital, "0111", ["O80"],
               [(bd, "0120", None, los), (bd, "0720", None, 1), (bd, "0250", None, 1, los), (bd, "0300", None, 1),
                (bd, "0270", None, 1)],
               admit=bd, discharge=bd + timedelta(days=los))
    prof_claim(mother.id, ob, "21", ["O80"], [(bd, "59400", 1, None)])
    inst_claim(baby_id, mother.hospital, "0111", ["Z38.00"], [(bd, "0170", None, los)], admit=bd,
               discharge=bd + timedelta(days=los))
    prof_claim(baby_id, pick(mother.state, "Pediatrics"), "21", ["Z38.00"], [(bd, "99460", 1, None)])


def gen_member_claims(p):
    for a, b in covered_intervals(p.id):
        yrs = ((b - a).days + 1) / 365.25
        age = p.age(a)

        def dates(rate):
            return sorted(rdate(a, b) for _ in range(poisson(rate * yrs)))

        # acute sick visits
        lam = 3.0 if age < 5 else 1.8 if age < 12 else 1.3 if age < 50 else 1.7
        for dt_ in dates(lam):
            acute_visit(p, dt_)
        # preventive (yearly)
        for yr in sorted({x.year for x in (a, b)} | ({2025, 2026} if a.year <= 2025 and b.year >= 2026 else set())):
            lo, hi = max(a, d(yr, 1, 1)), min(b, d(yr, 12, 31))
            if lo > hi:
                continue
            frac = ((hi - lo).days + 1) / 365.0
            pa = p.age(lo)
            if pa < 1:
                for k in range(R.randint(2, 4)):
                    dt_ = rdate(lo, hi)
                    preventive_visit(p, dt_)
            elif R.random() < (0.80 if pa < 18 else 0.60) * frac:
                preventive_visit(p, rdate(lo, hi))
            # flu shot in the fall
            flo, fhi = max(lo, d(yr, 9, 15)), min(hi, d(yr, 12, 15))
            if flo <= fhi and R.random() < 0.42:
                dt_ = rdate(flo, fhi)
                prof_claim(p.id, p.pcp, "11", ["Z23"], [(dt_, "90686", 1, None), (dt_, "90471", 1, None)])
            if p.gender == "F" and 40 <= pa <= 74 and R.random() < 0.55 * frac:
                prof_claim(p.id, pick(p.state, "Imaging Center"), "11", ["Z12.31"], [(rdate(lo, hi), "77067", 1, None)])
            if 45 <= pa <= 75 and not p.colo_done and R.random() < 0.07 * frac:
                screening_colonoscopy(p, rdate(lo, hi))
                p.colo_done = True
        # chronic care
        rate = (4 if p.dm else 0) + (2 if p.htn and not p.dm else 0) + (1 if p.lipid and not (p.dm or p.htn) else 0) \
            + (1.5 if p.thyroid and not (p.dm or p.htn) else 0) + (2 if (p.asthma or p.copd) and not p.dm else 0)
        for dt_ in dates(rate):
            chronic_visit(p, dt_)
        if p.cardiac:
            for dt_ in dates(3):
                cardiac_visit(p, dt_)
        if p.bh:
            for dt_ in dates(0.7):
                bh_episode(p, dt_, b)
        if age >= 18:
            for dt_ in dates(0.06):
                back_episode(p, dt_, b)
        if age >= 25:
            for dt_ in dates(0.03 + (0.03 if age >= 50 else 0)):
                knee_episode(p, dt_, b)
        er_rate = 0.22 if age < 12 else 0.17
        if p.cardiac or p.copd:
            er_rate += 0.15
        for dt_ in dates(er_rate):
            er_visit(p, dt_)
        ip_rate = 0.016 if age < 50 else 0.055
        if p.cardiac or p.copd:
            ip_rate += 0.12
        for dt_ in dates(ip_rate):
            if p.age(dt_) < 18:
                dx = wchoice([(["J18.9"], 40), (["J45.909"], 25), (["N39.0"], 15), (["L03.90"], 10), (["R10.9"], 10)])
            else:
                old = p.age(dt_) >= 50
                dx = wchoice([(["J18.9"], 30), (["I50.9", "I10"], 25 if p.cardiac else (3 if old else 0)),
                              (["J44.9"], 20 if p.copd else 0), (["I48.91"], 15 if p.cardiac else (2 if old else 0)),
                              (["N39.0"], 10), (["L03.90"], 8)])
            if dx == ["J18.9"] and 4 <= dt_.month <= 9 and R.random() < 0.6:
                dx = ["L03.90"] if R.random() < 0.5 else ["N39.0"]
            inpatient(p, dt_, dx, R.randint(2, 7))
        if age >= 25:
            for dt_ in dates(0.002):
                er_visit_gb = dt_
                gallbladder_surgery(p, er_visit_gb)
        if p.onc:
            st = rdate(a, min(b, d(2026, 6, 30)))
            if st >= a:
                chemo_course(p, st, b)
                p.onc = False

    # a doctor visit shortly after coverage ended (should be denied as not eligible)
    spans = sorted(MEM_SPANS[p.id], key=lambda s: s["effective_date"])
    last = spans[-1] if spans else None
    if last and last["term_date"] and SVC_START <= last["term_date"] < SVC_END and R.random() < 0.12:
        dt_ = last["term_date"] + timedelta(days=R.randint(3, 40))
        if dt_ <= SVC_END and not span_for(p.id, dt_):
            acute_visit(p, dt_, flags=("post_term",))


# --------------------------------------------------------------------------- receive, adjudicate

def receive_and_process():
    received = []
    for c in CLAIMS:
        base = 2 if c["ctype"] == "PROF" else 4
        lag = base + min(int(R.expovariate(1 / (12 if c["ctype"] == "PROF" else 18))), 150)
        if R.random() < 0.006:
            lag = R.randint(370, 470)
            c["flags"].add("late")
        c["received"] = c["to"] + timedelta(days=lag)
        if c["received"] > AS_OF:
            continue
        received.append(c)
    # resubmitted duplicates (provider sends the same claim again)
    dups = []
    for c in received:
        if c["ctype"] == "PROF" and "post_term" not in c["flags"] and "late" not in c["flags"] and R.random() < 0.015:
            nc = dict(c)
            nc["lines"] = [dict(l) for l in c["lines"]]
            nc["flags"] = set(c["flags"]) | {"dup"}
            nc["received"] = c["received"] + timedelta(days=R.randint(25, 70))
            nc["dup_of"] = c
            if nc["received"] <= AS_OF:
                dups.append(nc)
    received += dups
    for c in received:
        slow = R.random() < 0.04
        lo, hi = (1, 14) if c["ctype"] == "PROF" else (2, 21)
        c["processed"] = c["received"] + timedelta(days=R.randint(lo, hi) + (R.randint(15, 40) if slow else 0))
        while c["processed"].weekday() >= 5:
            c["processed"] += timedelta(days=1)
    return received


ACC = defaultdict(lambda: {"ded": 0.0, "oop": 0.0})


def plan_for(c):
    s = span_for(c["member"], c["frm"])
    if s:
        return s["plan_code"], s
    spans = sorted(MEM_SPANS.get(c["member"], []), key=lambda s: s["effective_date"])
    spans = [s for s in spans if not s.get("bogus")]
    return (spans[-1]["plan_code"] if spans else "PPO500"), None


def fee_on(code, dt_):
    base = FEES[code]
    return base if dt_.year <= 2025 else money(base * 1.03)


def price_line(c, l, prov):
    if c["ctype"] == "PROF":
        f = fee_on(l["code"], l["date"]) * l["units"] * (0.32 if l["mod"] == "26" else 1.0)
        if prov["network_status"] == "OON":
            f = f * 1.4
        return money(min(l["billed"], f))
    pct = prov["contract_pct_of_billed"] if prov["network_status"] == "INN" else 0.40
    return money(l["billed"] * pct)


def deny_all(c, code):
    c["status"], c["denial"] = "D", code
    for l in c["lines"]:
        l.update(allowed=0.0, paid=0.0, ded=0.0, copay=0.0, coins=0.0, lstatus="D", ldenial=code)


def adjudicate(c, pay_anyway_ids):
    prov = PROV[c["billing"]]
    c["network"] = prov["network_status"]
    c["denial"] = None
    if c["processed"] > FINAL_CUTOFF:
        c["status"] = "H"
        c["processed"] = None
        for l in c["lines"]:
            l.update(allowed=None, paid=None, ded=None, copay=None, coins=None, lstatus="H", ldenial=None)
        return
    plan_code, span = plan_for(c)
    plan = PLANS[plan_code]
    emergency = "emergency" in c["flags"]
    if span is None and id(c) not in pay_anyway_ids:
        return deny_all(c, "D01")
    if "dup" in c["flags"] and id(c) not in pay_anyway_ids:
        return deny_all(c, "D02")
    if "late" in c["flags"]:
        return deny_all(c, "D03")
    if c["network"] == "OON" and not plan["oon"] and not emergency:
        return deny_all(c, "D08")
    if "pa_check" in c["flags"] and R.random() < 0.05:
        return deny_all(c, "D04")
    if any(l["code"] in ("72148", "73721", "74177") for l in c["lines"]) and not emergency and R.random() < 0.04:
        return deny_all(c, "D04")
    x = R.random()
    if x < 0.007:
        return deny_all(c, "D06")
    if x < 0.0095:
        return deny_all(c, "D05")

    c["status"] = "P"
    oon_cs = c["network"] == "OON" and not emergency
    acc = ACC[(c["member"], c["frm"].year)]
    er_mode = "er_facility" in c["flags"] and plan["er"] > 0
    er_left = plan["er"] if er_mode else 0.0
    copay_used = False
    pcp = prov["provider_type"] == "INDIVIDUAL" and prov["specialty"] in PCP_SPECS
    for l in c["lines"]:
        if l.get("bundle_deny"):
            l.update(allowed=0.0, paid=0.0, ded=0.0, copay=0.0, coins=0.0, lstatus="D", ldenial="D07")
            continue
        allowed = price_line(c, l, prov)
        ded = cop = coi = 0.0
        oop_rem = max(0.0, plan["oop"] - acc["oop"])
        preventive = (l["code"] and PCAT.get(l["code"]) in ("Preventive", "Immunization")) or "screening" in c["flags"]
        if preventive and not oon_cs:
            pass
        elif er_mode:
            cop = money(min(allowed, er_left, oop_rem))
            er_left -= cop
        elif (not copay_used and l["code"] in COPAY_PCP_CODES and c["ctype"] == "PROF" and c["pos"] in ("10", "11")
              and plan["pcp"] > 0 and not oon_cs):
            amt = plan["pcp"] if (pcp or l["code"] in ("90791", "90834", "90837")) else plan["spec"]
            cop = money(min(amt, allowed, oop_rem))
            copay_used = True
        elif not copay_used and l["code"] in COPAY_SPEC_CODES and plan["spec"] > 0 and not oon_cs:
            cop = money(min(plan["spec"], allowed, oop_rem))
            copay_used = True
        else:
            ded_rem = max(0.0, plan["ded"] - acc["ded"])
            ded = money(min(allowed, ded_rem, oop_rem))
            pct = plan["oon_coins"] if oon_cs else plan["coins"]
            coi = money(min((allowed - ded) * pct, oop_rem - ded))
        acc["ded"] = money(acc["ded"] + ded)
        acc["oop"] = money(acc["oop"] + ded + cop + coi)
        paid = money(allowed - ded - cop - coi)
        l.update(allowed=allowed, paid=paid, ded=ded, copay=cop, coins=coi, lstatus="P", ldenial=None)
    if all(l["lstatus"] == "D" for l in c["lines"]):
        c["status"], c["denial"] = "D", "D07"


def payment_date(processed):
    dt_ = processed + timedelta(days=1)
    while dt_.weekday() not in (1, 4):      # payment runs Tuesday and Friday
        dt_ += timedelta(days=1)
    return dt_


def totals(c):
    def s(k):
        vals = [l[k] for l in c["lines"]]
        return None if any(v is None for v in vals) else money(sum(vals))
    c["t_billed"] = money(sum(l["billed"] for l in c["lines"]))
    for k in ("allowed", "paid", "ded", "copay", "coins"):
        c["t_" + k] = s(k)


# --------------------------------------------------------------------------- main

def main():
    os.makedirs(OUT, exist_ok=True)
    build_groups_and_members()
    by_state = defaultdict(int)
    for m in MEMBERS:
        by_state[m["address_state"]] += 1
    build_providers(by_state)

    people = {m["member_id"]: Person(m) for m in MEMBERS}
    for mid in sorted(people):
        gen_member_claims(people[mid])
    for mother_id, baby_id, bd in NEWBORN_EVENTS:
        if span_for(mother_id, bd) and SVC_START <= bd <= SVC_END:
            maternity(people[mother_id], baby_id, bd)
    # follow-up services can land outside coverage or the service window; keep only the ones the member was
    # covered for (the deliberate after-coverage visits are kept so they can be denied)
    CLAIMS[:] = [c for c in CLAIMS if SVC_START <= c["frm"] <= SVC_END
                 and ("post_term" in c["flags"] or span_for(c["member"], c["frm"]))]
    # two visits generated for the same person, same doctor, same day, same codes would look like a duplicate
    # submission; keep only one so the planted duplicates are the only ones
    seen, kept = set(), []
    for c in CLAIMS:
        key = (c["member"], c["billing"], c["frm"], c["ctype"],
               tuple(sorted((l["code"] or "", l["rev"] or "", l["units"]) for l in c["lines"])))
        if key not in seen:
            seen.add(key)
            kept.append(c)
    CLAIMS[:] = kept

    # ---- planted: duplicate provider records (same NPI, second provider_id); some claims bill under the copy
    indiv = [p for p in PROVIDERS if p["provider_type"] == "INDIVIDUAL" and p["specialty"] in PCP_SPECS]
    alias = {}
    for p in R.sample(indiv, 4):
        q = dict(p)
        _pseq[0] += 1
        q["provider_id"] = f"P{_pseq[0]:06d}"
        nm = p["provider_name"].split(",")[0]
        first, last = nm.split(" ", 1)
        q["provider_name"] = f"{last.upper()}, {first.upper()}"
        q["address_zip"] = rzip(p["address_state"])
        PROVIDERS.append(q)
        PROV[q["provider_id"]] = q
        alias[p["provider_id"]] = q["provider_id"]
        PLANT["provider_duplicate_npi"].append([p["provider_id"], q["provider_id"], p["npi"]])
    for c in CLAIMS:
        if c["billing"] in alias and R.random() < 0.4:
            c["billing"] = alias[c["billing"]]
            if c["rendering"]:
                c["rendering"] = c["billing"]
    for p in R.sample([p for p in PROVIDERS if p["provider_type"] == "INDIVIDUAL" and p["provider_id"] not in alias], 3):
        good = p["npi"]
        p["npi"] = good[:9] + str((int(good[9]) + R.randint(1, 9)) % 10)
        PLANT["provider_invalid_npi_checksum"].append(p["provider_id"])
    for p in R.sample([p for p in PROVIDERS if p["provider_type"] == "INDIVIDUAL"], 3):
        p["specialty"] = None
        PLANT["provider_missing_specialty"].append(p["provider_id"])

    # ---- planted: duplicate member records for 10 dependents
    deps = [m for m in MEMBERS if m["relationship_code"] == "DEP" and MEM_SPANS[m["member_id"]]]
    dup_map = {}
    for m in R.sample(deps, 10):
        nm = new_member(m["subscriber_id"], "DEP", m["first_name"], m["last_name"], m["birth_date"], m["gender"],
                        m["address_state"], m["address_zip"])
        last_span = sorted(MEM_SPANS[m["member_id"]], key=lambda s: s["effective_date"])[-1]
        add_span(nm["member_id"], last_span["group_id"], last_span["plan_code"], last_span["coverage_tier"],
                 last_span["effective_date"], last_span["term_date"])
        dup_map[m["member_id"]] = nm["member_id"]
        PLANT["member_duplicate_records"].append([m["member_id"], nm["member_id"]])
    for c in CLAIMS:
        if c["member"] in dup_map and R.random() < 0.3:
            nm = dup_map[c["member"]]
            if span_for(nm, c["frm"]):
                c["member"] = nm

    received = receive_and_process()

    # choose planted "paid when it should have been denied" cases
    post_term = [c for c in received if "post_term" in c["flags"] and c["processed"] <= FINAL_CUTOFF]
    pay_anyway = set(id(c) for c in R.sample(post_term, min(30, len(post_term))))
    dups = [c for c in received if "dup" in c["flags"] and c["processed"] <= FINAL_CUTOFF]
    pay_dups = set(id(c) for c in R.sample(dups, min(40, len(dups))))
    pay_ids = pay_anyway | pay_dups

    received.sort(key=lambda c: (c["processed"], c["received"], c["member"]))
    for c in received:
        adjudicate(c, pay_ids)
        c["paid_date"] = payment_date(c["processed"]) if c["status"] == "P" else None
        c["original"] = None
        totals(c)

    # ---- adjustments on ~2% of paid claims: the original underpaid one line (member share was a flat copay or $0,
    # so only the plan's payment was wrong). The provider appealed; the replacement (A) pays the correct amount and
    # the original is reversed (X).
    adjustments = []
    dup_origs = set(id(c["dup_of"]) for c in received if id(c) in pay_dups)
    for c in received:
        if (c["status"] != "P" or c["processed"] > AS_OF - timedelta(days=40) or id(c) in pay_ids or id(c) in dup_origs
                or R.random() > 0.02):
            continue
        cands = [i for i, l in enumerate(c["lines"]) if l["lstatus"] == "P" and l["ded"] == 0 and l["coins"] == 0
                 and l["paid"] >= 20]
        if not cands:
            continue
        received_a = c["processed"] + timedelta(days=R.randint(10, 60))
        if received_a > AS_OF - timedelta(days=8):
            continue
        nc = {k: v for k, v in c.items() if k != "lines"}
        nc["lines"] = [dict(l) for l in c["lines"]]
        nc["flags"] = set(c["flags"]) | {"adjustment"}
        nc["received"] = received_a
        nc["processed"] = received_a + timedelta(days=R.randint(1, 7))
        while nc["processed"].weekday() >= 5:
            nc["processed"] += timedelta(days=1)
        nc["status"] = "A"
        nc["original"] = c
        nc["paid_date"] = payment_date(nc["processed"])
        totals(nc)
        ol = c["lines"][R.choice(cands)]
        delta = money(ol["paid"] * R.uniform(0.10, 0.40))
        ol["allowed"] = money(ol["allowed"] - delta)
        ol["paid"] = money(ol["paid"] - delta)
        totals(c)
        c["status"] = "X"
        adjustments.append(nc)
    received += adjustments

    # ---- claim ids in order received
    received.sort(key=lambda c: (c["received"], c["ctype"], c["member"], c["frm"]))
    for i, c in enumerate(received, 1):
        c["claim_id"] = f"C{c['received'].year % 100:02d}{i:07d}"

    # ---- planted: data problems on the claim extract
    paid_prof = [c for c in received if c["status"] == "P" and c["ctype"] == "PROF" and not c["flags"] & {"post_term", "dup"}]
    for i, c in enumerate(R.sample(paid_prof, 15)):
        c["member"] = f"M{9800001 + i:07d}"
        PLANT["claims_orphan_member_id"].append(c["claim_id"])
    pool = [c for c in received if c["status"] in ("P", "D") and c["claim_id"] not in PLANT["claims_orphan_member_id"]]
    for c in R.sample(pool, 20):
        c["t_billed"] = money(c["t_billed"] + R.randint(50, 500))
        PLANT["claims_header_billed_not_equal_lines"].append(c["claim_id"])
    for c in R.sample([c for c in pool if c["frm"].year == 2026 and c["claim_id"] not in PLANT["claims_header_billed_not_equal_lines"]], 3):
        c["frm"] = c["frm"].replace(year=2027)
        c["to"] = c["to"].replace(year=2027)
        PLANT["claims_service_date_typo_2027"].append(c["claim_id"])
    dotless_provs = set(R.sample([p["provider_id"] for p in PROVIDERS if p["provider_type"] == "INDIVIDUAL"], 8))
    for c in received:
        if c["billing"] in dotless_provs:
            c["dx"] = [x.replace(".", "") for x in c["dx"]]
            c["flags"].add("dotless")
    PLANT["dx_codes_without_dots_billing_providers"] = sorted(dotless_provs)
    PLANT["dx_codes_without_dots_claim_count"] = sum(1 for c in received if "dotless" in c["flags"])
    PLANT["claims_paid_member_not_eligible"] = sorted(c["claim_id"] for c in received
                                                      if id(c) in pay_anyway and c["status"] == "P")
    PLANT["claims_paid_duplicate_submission"] = sorted(
        [c["dup_of"]["claim_id"], c["claim_id"]] for c in received
        if id(c) in pay_dups and c["status"] == "P" and c["dup_of"]["status"] in ("P", "X"))
    PLANT["claims_denied_duplicate_submission_D02"] = sum(1 for c in received if c.get("denial") == "D02")

    # ---- planted: eligibility problems
    pc_group = GROUPS[0]["group_id"]
    pc_members = sorted({s["member_id"] for s in SPANS if s["group_id"] == pc_group and s["plan_code"] == "PPO500"
                         and s["term_date"] == d(2025, 12, 31)})
    for mid in R.sample(pc_members, min(25, len(pc_members))):
        for s in MEM_SPANS[mid]:
            if s["plan_code"] == "PPO500" and s["term_date"] == d(2025, 12, 31):
                s["term_date"] = d(2026, 3, 31)
        PLANT["eligibility_overlapping_spans_members"].append(mid)
    for mid in R.sample([m["member_id"] for m in MEMBERS if MEM_SPANS[m["member_id"]]], 3):
        s0 = sorted(MEM_SPANS[mid], key=lambda s: s["effective_date"])[-1]
        eff = add_months(max(s0["effective_date"], d(2025, 3, 1)), 2)
        row = add_span(mid, s0["group_id"], s0["plan_code"], s0["coverage_tier"], eff, eff - timedelta(days=1))
        row["bogus"] = True
        PLANT["eligibility_term_before_effective_members"].append(mid)

    # ---- planted: member data quality
    dup_ids = {x for pair in PLANT["member_duplicate_records"] for x in pair}
    for m in MEMBERS:
        x = R.random()
        if x < 0.012:
            m["gender"] = {"M": "Male", "F": "Female"}[m["gender"]]
        elif x < 0.02:
            m["gender"] = m["gender"].lower()
        elif x < 0.025:
            m["gender"] = "U"
        elif x < 0.028:
            m["gender"] = None
        if R.random() < 0.01 and m["member_id"] not in dup_ids:
            m["last_name"] = m["last_name"] + " "
            PLANT["member_last_name_trailing_space"].append(m["member_id"])
        if m["address_state"] in LEADING_ZERO_STATES and R.random() < 0.25:
            m["address_zip"] = m["address_zip"].lstrip("0")
            PLANT["member_zip_lost_leading_zero"].append(m["member_id"])
    for m in R.sample([m for m in MEMBERS if m["relationship_code"] == "DEP"], 5):
        m["birth_date"] = None
        PLANT["member_missing_birth_date"].append(m["member_id"])

    PLANT["members_with_no_eligibility"] = [m["member_id"] for m in MEMBERS if not MEM_SPANS[m["member_id"]]]
    write_all(received)
    if SPOILERS:
        with open(SPOILERS, "w") as f:
            json.dump(PLANT, f, indent=1, default=str)


# --------------------------------------------------------------------------- output

def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.2f}"
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def write(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for r in rows:
            w.writerow([fmt(x) for x in r])


def write_all(claims):
    write("procedure_codes.csv", ["procedure_code", "description", "category"], [(c, d_, cat) for c, d_, cat, _ in PROCS])
    fs = []
    for c, _, _, f in PROCS:
        fs.append((c, float(f), d(2025, 1, 1), d(2025, 12, 31)))
        fs.append((c, money(f * 1.03), d(2026, 1, 1), OPEN_END))
    write("fee_schedule.csv", ["procedure_code", "allowed_amt", "effective_date", "term_date"], fs)
    write("revenue_codes.csv", ["revenue_code", "description"], REVS)
    write("diagnosis_codes.csv", ["dx_code", "description", "category"], DX)
    write("denial_reasons.csv", ["denial_reason_code", "description"], DENIALS)
    write("place_of_service.csv", ["pos_code", "description"], POS)
    write("claim_status_codes.csv", ["claim_status", "description"], STATUSES)
    write("plans.csv", ["plan_code", "plan_name", "plan_type", "deductible_amt", "oop_max_amt", "coinsurance_pct",
                        "oon_covered_flag", "oon_coinsurance_pct", "pcp_copay_amt", "specialist_copay_amt", "er_copay_amt"],
          [(k, p["name"], p["type"], float(p["ded"]), float(p["oop"]), p["coins"], "Y" if p["oon"] else "N",
            p["oon_coins"], float(p["pcp"]), float(p["spec"]), float(p["er"])) for k, p in PLANS.items()])
    write("employer_groups.csv", ["group_id", "group_name", "industry", "state", "effective_date", "term_date"],
          [(g["group_id"], g["group_name"], g["industry"], g["state"], g["effective_date"], g["term_date"]) for g in GROUPS])
    write("members.csv", ["member_id", "subscriber_id", "relationship_code", "first_name", "last_name", "birth_date",
                          "gender", "address_state", "address_zip"],
          [(m["member_id"], m["subscriber_id"], m["relationship_code"], m["first_name"], m["last_name"], m["birth_date"],
            m["gender"], m["address_state"], m["address_zip"]) for m in MEMBERS])
    rows = []
    for i, s in enumerate(sorted(SPANS, key=lambda s: (s["member_id"], s["effective_date"])), 1):
        term = s["term_date"]
        if term is None:
            # two different conventions for "still active" from two load processes
            term_out = OPEN_END if s["effective_date"] < d(2025, 6, 1) else None
        else:
            term_out = term
        rows.append((100000 + i, s["member_id"], s["group_id"], s["plan_code"], s["coverage_tier"], s["effective_date"], term_out))
    write("eligibility.csv", ["eligibility_id", "member_id", "group_id", "plan_code", "coverage_tier", "effective_date",
                              "term_date"], rows)
    write("providers.csv", ["provider_id", "npi", "provider_name", "provider_type", "specialty", "address_state",
                            "address_zip", "network_status", "contract_pct_of_billed"],
          [(p["provider_id"], p["npi"], p["provider_name"], p["provider_type"], p["specialty"], p["address_state"],
            p["address_zip"], p["network_status"], p["contract_pct_of_billed"]) for p in PROVIDERS])

    hdr = ["claim_id", "claim_type", "member_id", "billing_provider_id", "rendering_provider_id", "network_status",
           "bill_type", "place_of_service", "admit_date", "discharge_date", "service_from_date", "service_to_date",
           "received_date", "processed_date", "paid_date", "claim_status", "denial_reason_code", "original_claim_id",
           "dx_code_1", "dx_code_2", "dx_code_3", "dx_code_4", "total_billed_amt", "total_allowed_amt",
           "total_paid_amt", "deductible_amt", "copay_amt", "coinsurance_amt"]
    lhdr = ["claim_id", "line_number", "service_date", "procedure_code", "modifier_1", "revenue_code", "units",
            "billed_amt", "allowed_amt", "paid_amt", "deductible_amt", "copay_amt", "coinsurance_amt", "line_status",
            "denial_reason_code"]
    hrows, lrows = [], []
    for c in claims:
        dx = (c["dx"] + [None] * 4)[:4]
        hrows.append([c["claim_id"], c["ctype"], c["member"], c["billing"], c["rendering"], c["network"], c["bill_type"],
                      c["pos"], c["admit"], c["discharge"], c["frm"], c["to"], c["received"], c["processed"],
                      c["paid_date"], c["status"], c["denial"], c["original"]["claim_id"] if c["original"] else None,
                      *dx, c["t_billed"], c["t_allowed"], c["t_paid"], c["t_ded"], c["t_copay"], c["t_coins"]])
        for n, l in enumerate(c["lines"], 1):
            lrows.append([c["claim_id"], n, l["date"], l["code"], l["mod"], l["rev"], l["units"], l["billed"],
                          l["allowed"], l["paid"], l["ded"], l["copay"], l["coins"], l["lstatus"], l["ldenial"]])
    # planted: the same claim rows extracted twice (12 headers, lines for 8 of them)
    picks = R.sample(range(len(hrows)), 12)
    for k, i in enumerate(picks):
        cid = hrows[i][0]
        PLANT["claims_exact_duplicate_rows"].append(cid)
        hrows.append(list(hrows[i]))
        if k < 8:
            lrows += [list(r) for r in lrows if r[0] == cid]
            PLANT["claim_lines_exact_duplicate_rows_for"].append(cid)
    R.shuffle(hrows)
    write("claims.csv", hdr, hrows)
    write("claim_lines.csv", lhdr, lrows)


if __name__ == "__main__":
    main()
