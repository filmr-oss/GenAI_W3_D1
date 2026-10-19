import os
import re

from dotenv import load_dotenv
from Neo4j.scraper import fetch_tn_schemes
from langchain_neo4j import Neo4jGraph


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# CONNECT TO NEO4J
# ============================================================

graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE"),
)


print("========================================")
print("🌾 Building Tamil Nadu Scheme Knowledge Graph")
print("========================================")


# ============================================================
# FIELD EXTRACTION
# ============================================================

def get_field(text, field_name, next_fields):

    pattern = (
        rf"{re.escape(field_name)}:\s*"
        rf"(.*?)(?=\n(?:{'|'.join(map(re.escape, next_fields))}):|\Z)"
    )

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if match:
        return match.group(1).strip()

    return ""


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_value(value):

    if not value:
        return ""

    # Normalize Windows/Mac line endings
    value = value.replace("\r\n", "\n")
    value = value.replace("\r", "\n")

    # Remove excessive whitespace
    value = re.sub(r"\s+", " ", value)

    return value.strip()


# ============================================================
# NORMALIZE SCHEME NAME
# ============================================================

def normalize_scheme_name(name):

    name = clean_value(name)

    if not name:
        return ""

    # Fix accidental missing spaces
    # Example:
    # Trainingto Farmers
    # Training ToFarmers
    # TrainingtoFarmers

    name = re.sub(
        r"(?i)\btraining\s*to\s*farmers\b",
        "Training to Farmers",
        name
    )

    # General cleanup around "to"
    name = re.sub(
        r"(?i)([a-z])to([A-Z])",
        r"\1 to \2",
        name
    )

    # Remove duplicate spaces
    name = re.sub(r"\s+", " ", name)

    return name.strip()


# ============================================================
# FIELDS PRESENT IN GOVERNMENT PAGE
# ============================================================

FIELDS = [
    "Concerned Department",
    "Concerned District",
    "Organisation Name",
    "Department",
    "Scheme Details",
    "Scheme Title/Name",
    "Associated Scheme",
    "Sponsered By",
    "Funding Pattern",
    "Beneficiaries",
    "Types of Benefits",
    "Eligibility criteria",
    "Income",
    "Age From",
    "Age To",
    "Community",
    "How To avail",
    "The application is to be submitted",
    "Validity of the Scheme",
    "Introduced On",
    "Description",
    "Scheme Type",
    "Uploaded File",
]


# ============================================================
# SCRAPE GOVERNMENT WEBSITE
# ============================================================

print("\n📥 Scraping Tamil Nadu Government schemes...")

docs = fetch_tn_schemes(limit=None)

print(f"\n✅ Total schemes scraped: {len(docs)}")


# ============================================================
# CLEAR OLD GRAPH
# ============================================================

print("\n🧹 Clearing old graph...")

graph.query("""
MATCH (n)
DETACH DELETE n
""")

print("✅ Old graph cleared")


# ============================================================
# PROCESS SCHEMES
# ============================================================

successful = 0


for index, doc in enumerate(docs, start=1):

    text = doc.page_content

    print(f"\n[{index}/{len(docs)}] Processing scheme...")


    # ========================================================
    # EXTRACT FIELDS
    # ========================================================

    scheme_name = doc.metadata.get("scheme", "")

    department = get_field(
        text,
        "Concerned Department",
        FIELDS
    )

    beneficiaries = get_field(
        text,
        "Beneficiaries",
        FIELDS
    )

    benefits = get_field(
        text,
        "Types of Benefits",
        FIELDS
    )

    funding = get_field(
        text,
        "Funding Pattern",
        FIELDS
    )

    eligibility = get_field(
        text,
        "Eligibility criteria",
        FIELDS
    )

    application = get_field(
        text,
        "The application is to be submitted",
        FIELDS
    )

    description = get_field(
        text,
        "Description",
        FIELDS
    )

    scheme_type = get_field(
        text,
        "Scheme Type",
        FIELDS
    )

    source_url = doc.metadata.get("source", "")


    # ========================================================
    # CLEAN VALUES
    # ========================================================

    scheme_name = normalize_scheme_name(
        scheme_name
    )

    department = clean_value(
        department
    )

    beneficiaries = clean_value(
        beneficiaries
    )

    benefits = clean_value(
        benefits
    )

    funding = clean_value(
        funding
    )

    eligibility = clean_value(
        eligibility
    )

    application = clean_value(
        application
    )

    description = clean_value(
        description
    )

    scheme_type = clean_value(
        scheme_type
    )


    # ========================================================
    # FIX ELIGIBILITY
    #
    # Government website often leaves:
    #
    # Eligibility criteria:
    # Income:
    # Age From:
    # Age To:
    # Community:
    #
    # empty.
    #
    # The actual eligibility information is often inside
    # Description.
    # ========================================================

    invalid_eligibility_values = {
        "",
        "income:",
        "age from:",
        "age to:",
        "community:",
        "income",
        "age from",
        "age to",
        "community",
        "-"
    }


    if (
        not eligibility
        or eligibility.lower() in invalid_eligibility_values
    ):

        eligibility = description


    # ========================================================
    # SKIP INVALID SCHEMES
    # ========================================================

    if not scheme_name:

        print("⚠️ Skipping scheme with no name")

        continue


    # ========================================================
    # CREATE SCHEME NODE
    # ========================================================

    graph.query(
        """
        MERGE (s:Scheme {id: $scheme})

        SET
            s.description = $description,
            s.funding = $funding,
            s.scheme_type = $scheme_type,
            s.source = $source
        """,

        params={
            "scheme": scheme_name,
            "description": description,
            "funding": funding,
            "scheme_type": scheme_type,
            "source": source_url,
        }
    )


    # ========================================================
    # DEPARTMENT
    # ========================================================

    if department and department != "-":

        graph.query(
            """
            MERGE (d:Department {id: $department})

            WITH d

            MATCH (s:Scheme {id: $scheme})

            MERGE (s)-[:OFFERED_BY]->(d)
            """,

            params={
                "department": department,
                "scheme": scheme_name
            }
        )


    # ========================================================
    # BENEFICIARY
    # ========================================================

    if beneficiaries and beneficiaries != "-":

        graph.query(
            """
            MERGE (b:Beneficiary {id: $beneficiary})

            WITH b

            MATCH (s:Scheme {id: $scheme})

            MERGE (s)-[:APPLIES_TO]->(b)
            """,

            params={
                "beneficiary": beneficiaries,
                "scheme": scheme_name
            }
        )


    # ========================================================
    # BENEFIT
    # ========================================================

    if benefits and benefits != "-":

        graph.query(
            """
            MERGE (b:Benefit {id: $benefit})

            WITH b

            MATCH (s:Scheme {id: $scheme})

            MERGE (s)-[:PROVIDES_BENEFIT]->(b)
            """,

            params={
                "benefit": benefits,
                "scheme": scheme_name
            }
        )


    # ========================================================
    # ELIGIBILITY CRITERIA
    # ========================================================

    if eligibility and eligibility != "-":

        graph.query(
            """
            MERGE (e:EligibilityCriteria {id: $eligibility})

            WITH e

            MATCH (s:Scheme {id: $scheme})

            MERGE (s)-[:HAS_CRITERIA]->(e)
            """,

            params={
                "eligibility": eligibility,
                "scheme": scheme_name
            }
        )


    # ========================================================
    # APPLICATION PROCESS
    # ========================================================

    if application and application != "-":

        graph.query(
            """
            MERGE (a:ApplicationProcess {id: $application})

            WITH a

            MATCH (s:Scheme {id: $scheme})

            MERGE (s)-[:HAS_APPLICATION_PROCESS]->(a)
            """,

            params={
                "application": application,
                "scheme": scheme_name
            }
        )


    successful += 1

    print(
        f"   ✅ {scheme_name}"
    )


# ============================================================
# GRAPH STATISTICS
# ============================================================

print("\n========================================")
print("🎉 GRAPH BUILD COMPLETE")
print("========================================")

print(
    f"Schemes processed: {successful}"
)


# ============================================================
# NODE STATISTICS
# ============================================================

result = graph.query(
    """
    MATCH (n)

    RETURN
        labels(n) AS label,
        count(n) AS count

    ORDER BY count DESC
    """
)


print("\n📊 Node statistics:")

for row in result:

    print(row)


# ============================================================
# RELATIONSHIP STATISTICS
# ============================================================

relationships = graph.query(
    """
    MATCH ()-[r]->()

    RETURN
        type(r) AS relationship,
        count(r) AS count

    ORDER BY count(r) DESC
    """
)


print("\n🔗 Relationship statistics:")

for row in relationships:

    print(row)


# ============================================================
# FINAL MESSAGE
# ============================================================

print("\n========================================")
print("✅ Knowledge graph ready!")
print("========================================")