import http from "k6/http";
import { sleep } from "k6";

export const options = {
  scenarios: {
    search_traffic: {
      executor: "constant-arrival-rate",
      rate: 20,
      timeUnit: "1s",
      duration: "5m",
      preAllocatedVUs: 20,
      exec: "search",
    },
    order_traffic: {
      executor: "constant-arrival-rate",
      rate: 5,
      timeUnit: "1s",
      duration: "5m",
      preAllocatedVUs: 10,
      exec: "createOrder",
    },
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export function search() {
  http.get(`${BASE_URL}/api/search?q=widget`);
  sleep(0.1);
}

export function createOrder() {
  http.post(`${BASE_URL}/api/orders`);
  sleep(0.1);
}
