// Optional development seed data for tax_db.
// Inserts one example corporation if the collection is empty.

const db = db.getSiblingDB("tax_db");

if (db.corporations.countDocuments({}) === 0) {
  db.corporations.insertOne({
    _id: "000000000000000000000001",
    name: "Demo Corp Inc.",
    corp_number: "1234567",
    business_number: "123456789RT0001",
    gst_hst_number: null,
    province: "ON",
    fiscal_year_end_month: 12,
    incorporation_date: "2020-01-15",
    contact_email: "demo@example.com",
    created_at: new Date().toISOString(),
  });
  print("tax_db seed: inserted Demo Corp Inc.");
} else {
  print("tax_db seed: skipped (collection not empty)");
}
