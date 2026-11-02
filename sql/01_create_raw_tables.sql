/* =====================================================================
   01_create_raw_tables.sql
   Raw landing tables for the practice claims data. One table per CSV.

   Run this in Lesson 1, AFTER you have created the CLAIMS_DB database
   and its RAW schema. Safe to re-run: CREATE OR REPLACE drops and
   recreates each table (empty).

   Type choices worth noticing:
   - IDs, NPIs, ZIP codes, bill types, place of service, revenue codes
     and procedure/diagnosis codes are VARCHAR, never NUMBER. They are
     labels, not quantities, and several start with a zero
     (ZIP 02134, bill type 0131, POS 02, revenue code 0450).
   - Money is NUMBER(12,2). Dates are DATE. Blank CSV fields load as NULL.
   ===================================================================== */

USE SCHEMA CLAIMS_DB.RAW;

CREATE OR REPLACE TABLE employer_groups (
    group_id        VARCHAR,
    group_name      VARCHAR,
    industry        VARCHAR,
    state           VARCHAR,
    effective_date  DATE,
    term_date       DATE
);

CREATE OR REPLACE TABLE plans (
    plan_code             VARCHAR,
    plan_name             VARCHAR,
    plan_type             VARCHAR,
    deductible_amt        NUMBER(12,2),
    oop_max_amt           NUMBER(12,2),
    coinsurance_pct       NUMBER(4,2),
    oon_covered_flag      VARCHAR,
    oon_coinsurance_pct   NUMBER(4,2),
    pcp_copay_amt         NUMBER(12,2),
    specialist_copay_amt  NUMBER(12,2),
    er_copay_amt          NUMBER(12,2)
);

CREATE OR REPLACE TABLE members (
    member_id          VARCHAR,
    subscriber_id      VARCHAR,
    relationship_code  VARCHAR,
    first_name         VARCHAR,
    last_name          VARCHAR,
    birth_date         DATE,
    gender             VARCHAR,
    address_state      VARCHAR,
    address_zip        VARCHAR
);

CREATE OR REPLACE TABLE eligibility (
    eligibility_id  NUMBER(10,0),
    member_id       VARCHAR,
    group_id        VARCHAR,
    plan_code       VARCHAR,
    coverage_tier   VARCHAR,
    effective_date  DATE,
    term_date       DATE
);

CREATE OR REPLACE TABLE providers (
    provider_id             VARCHAR,
    npi                     VARCHAR,
    provider_name           VARCHAR,
    provider_type           VARCHAR,
    specialty               VARCHAR,
    address_state           VARCHAR,
    address_zip             VARCHAR,
    network_status          VARCHAR,
    contract_pct_of_billed  NUMBER(4,2)
);

CREATE OR REPLACE TABLE claims (
    claim_id               VARCHAR,
    claim_type             VARCHAR,
    member_id              VARCHAR,
    billing_provider_id    VARCHAR,
    rendering_provider_id  VARCHAR,
    network_status         VARCHAR,
    bill_type              VARCHAR,
    place_of_service       VARCHAR,
    admit_date             DATE,
    discharge_date         DATE,
    service_from_date      DATE,
    service_to_date        DATE,
    received_date          DATE,
    processed_date         DATE,
    paid_date              DATE,
    claim_status           VARCHAR,
    denial_reason_code     VARCHAR,
    original_claim_id      VARCHAR,
    dx_code_1              VARCHAR,
    dx_code_2              VARCHAR,
    dx_code_3              VARCHAR,
    dx_code_4              VARCHAR,
    total_billed_amt       NUMBER(12,2),
    total_allowed_amt      NUMBER(12,2),
    total_paid_amt         NUMBER(12,2),
    deductible_amt         NUMBER(12,2),
    copay_amt              NUMBER(12,2),
    coinsurance_amt        NUMBER(12,2)
);

CREATE OR REPLACE TABLE claim_lines (
    claim_id            VARCHAR,
    line_number         NUMBER(4,0),
    service_date        DATE,
    procedure_code      VARCHAR,
    modifier_1          VARCHAR,
    revenue_code        VARCHAR,
    units               NUMBER(6,0),
    billed_amt          NUMBER(12,2),
    allowed_amt         NUMBER(12,2),
    paid_amt            NUMBER(12,2),
    deductible_amt      NUMBER(12,2),
    copay_amt           NUMBER(12,2),
    coinsurance_amt     NUMBER(12,2),
    line_status         VARCHAR,
    denial_reason_code  VARCHAR
);

CREATE OR REPLACE TABLE fee_schedule (
    procedure_code  VARCHAR,
    allowed_amt     NUMBER(12,2),
    effective_date  DATE,
    term_date       DATE
);

CREATE OR REPLACE TABLE procedure_codes (
    procedure_code  VARCHAR,
    description     VARCHAR,
    category        VARCHAR
);

CREATE OR REPLACE TABLE revenue_codes (
    revenue_code  VARCHAR,
    description   VARCHAR
);

CREATE OR REPLACE TABLE diagnosis_codes (
    dx_code      VARCHAR,
    description  VARCHAR,
    category     VARCHAR
);

CREATE OR REPLACE TABLE denial_reasons (
    denial_reason_code  VARCHAR,
    description         VARCHAR
);

CREATE OR REPLACE TABLE place_of_service (
    pos_code     VARCHAR,
    description  VARCHAR
);

CREATE OR REPLACE TABLE claim_status_codes (
    claim_status  VARCHAR,
    description   VARCHAR
);

SHOW TABLES IN SCHEMA CLAIMS_DB.RAW;   -- expect 14 tables

