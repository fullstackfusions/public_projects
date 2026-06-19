# Marketplace Feature

React frontend demonstrating contract-first design with FastAPI backend.

## Architecture

```
┌─────────────┐      HTTP/OpenAPI      ┌──────────────────┐
│   React UI  │ ────────────────────> │ Marketplace API  │
│             │   POST /orders          │   (FastAPI)      │
└─────────────┘                         └──────────────────┘
                                                │
                                                │ Kafka Event
                                                │ (AsyncAPI)
                                                ▼
                                        ┌──────────────────┐
                                        │ Payment Consumer │
                                        └──────────────────┘
```

## Features

- **Create Orders**: Submit orders via HTTP API
- **Contract Validation**: TypeScript types match OpenAPI schema
- **Real-time Feedback**: Immediate response from API
- **Error Handling**: Displays API errors gracefully

## API Contract

The frontend consumes the OpenAPI contract from `marketplace-api`:

**Endpoint**: `POST /orders`
**Request**:
```typescript
{
  user_id: string;
  amount_cents: number;
}
```

**Response**:
```typescript
{
  order_id: string;
  status: string;
}
```

## Integration

The API client (`src/api/marketplace.ts`) handles:
- HTTP requests to FastAPI backend
- Type-safe request/response handling
- Error handling and retry logic

## Environment Variables

- `VITE_MARKETPLACE_API_URL`: Marketplace API base URL (default: `http://localhost:8000`)

## Usage

```tsx
import MarketplacePage from './features/marketplace/MarketplacePage';

// In your router
<Route path="/marketplace" element={<MarketplacePage />} />
```

## Event Flow

1. User creates order in React UI
2. React calls `POST /orders` (OpenAPI contract)
3. FastAPI validates request, creates order
4. FastAPI publishes `OrderCreatedEvent` to Kafka topic `orders.created`
5. Payment consumer (consumer group `payment-service-v1`) receives event
6. Payment consumer validates event (AsyncAPI contract) and creates payment
7. React receives order confirmation

## Data Contracts

- **Orders**: Owned by Marketplace API service
- **Payments**: Owned by Payment Consumer service
- **Integration**: Via API (HTTP) and Events (Kafka), NOT shared database
