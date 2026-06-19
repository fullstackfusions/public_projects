// MongoDB index init script for tax_db.
// Executed once at container first-start via /docker-entrypoint-initdb.d/.
// Idempotent — createIndex is a no-op when the index already exists.

const db = db.getSiblingDB("tax_db");

// corporations
db.corporations.createIndex({ name: 1 });

// tax_filing_records
db.tax_filing_records.createIndex({ corp_id: 1 });
db.tax_filing_records.createIndex({ due_date: 1 });
db.tax_filing_records.createIndex(
  { corp_id: 1, filing_type: 1, period_label: 1 },
  { unique: true }
);

// nil_t2_reports
db.nil_t2_reports.createIndex({ corp_id: 1 });
db.nil_t2_reports.createIndex(
  { corp_id: 1, fiscal_year_end: 1 },
  { unique: true }
);

print("tax_db indexes created");
