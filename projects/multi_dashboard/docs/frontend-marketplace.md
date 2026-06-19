# Frontend: Marketplace

A form that submits orders to the marketplace API, which publishes them as Kafka events. The frontend only talks to the marketplace API — the payment processing happens asynchronously in the background via Kafka.

---

## What You'll Learn

- How the frontend interacts with an event-driven backend
- Fire-and-forget pattern: the API confirms the event was published, not that payment is complete
- Why the UI can show "Order placed!" without waiting for payment to finish

---

## How It Works

```
User fills in User ID + amount → clicks Submit
  → Frontend: POST /orders to marketplace-api
  ← Backend: 201 Created (event was published to Kafka)
  → Frontend: shows success message ✓

Meanwhile (invisible to user):
  Kafka delivers the event to payment-consumer
  payment-consumer creates a payment record
```

The frontend doesn't know about Kafka. It just calls a REST endpoint and gets a 201.

---

## File Structure

```
src/features/marketplace/
├── MarketplacePage.tsx    # Order form UI
└── types.ts               # TypeScript interfaces

src/api/
└── marketplace.ts         # API client
```

---

## Key Concept

The marketplace API returns immediately after publishing to Kafka — it does NOT wait for the payment consumer to finish. This is the whole point of event-driven architecture: the order service and payment service are decoupled.

If you want to verify the payment was processed, check the payment consumer logs:
```bash
docker compose logs payment-consumer | grep "Created payment"
```
