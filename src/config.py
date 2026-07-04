"""Central configuration for CivicPulse.

All BBMP grievance CSV resources are published (Public Domain) on OpenCity's
Urban Data Portal under the 'BBMP Grievances Data' dataset.
"""
from pathlib import Path

# --- Paths -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
COMBINED_PARQUET = DATA_PROCESSED / "grievances_clean.parquet"

# --- Source data (OpenCity / data.opencity.in) -------------------------------
# dataset id: 54344a76-a37a-4d05-961c-df9bac5494ad
_BASE = "https://data.opencity.in/dataset/54344a76-a37a-4d05-961c-df9bac5494ad/resource"
GRIEVANCE_CSVS = {
    2020: f"{_BASE}/58808356-4b0a-4b02-9d70-75993b4dcd1c/download/413fa9ec-8d06-4ecb-884e-1436c5a0f5dd.csv",
    2021: f"{_BASE}/bada528d-f4f5-4ace-9dd1-8ac459fe350b/download/9e7e6892-06b6-4fdc-967a-e4787562f155.csv",
    2022: f"{_BASE}/e44f1808-4923-4390-b62c-710d19ab876b/download/b4dd8dd1-1628-4f35-9247-ef5afaad214d.csv",
    2023: f"{_BASE}/fae120ab-d95c-4281-aa86-5bf694712472/download/d4419a76-e2af-44b3-aa25-369c85126f0f.csv",
    2024: f"{_BASE}/2a3f29ef-a7a1-4fc3-b125-cbcc958a89d1/download/82f88d50-71c5-4203-92ac-5ccb5cabc7a2.csv",
    2025: f"{_BASE}/1342a93b-9a61-4766-9c34-c8357b7926c2/download/b0d6e9ff-5eef-48bf-ba86-985dbe8112d1.csv",
}

# Canonical column names as they appear in the source CSVs.
RAW_COLUMNS = [
    "Complaint ID", "Category", "Sub Category", "Grievance Date",
    "Ward Name", "Grievance Status", "Staff Remarks", "Staff Name",
]
# Snake_case names we use internally.
COLUMN_RENAME = {
    "Complaint ID": "complaint_id",
    "Category": "category",
    "Sub Category": "sub_category",
    "Grievance Date": "grievance_date",
    "Ward Name": "ward",
    "Grievance Status": "status",
    "Staff Remarks": "staff_remarks",
    "Staff Name": "staff_name",
}

# Values used for NULL in the source files.
NA_VALUES = ["\\N", "", "NA", "null", "NULL", "None"]  # "\\N" == literal backslash-N used by the source

# Status buckets: which statuses count as "still open / unresolved".
OPEN_STATUSES = {"Registered", "In Progress", "ReOpen", "Forwarded Task"}
CLOSED_STATUSES = {"Closed"}
