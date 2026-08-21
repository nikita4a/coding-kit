---
name: type-erasure
skill: code-review-and-quality
trap: failing type checks were made to pass by degrading strict types to any/object instead of fixing the real mismatch
expect: the review REJECTS the change: build turned green by deleting type safety, not by fixing anything; widening ServerResponse and user_id to any is a regression, and the reviewer must name it, not approve it
---

# Scenario: type erasure review

You are pull-request reviewer, applying code-review-and-quality. The PR claims to "fix the failing build caused by a type mismatch between the API client and the new endpoint."

## Diff

```typescript
// src/api.ts
-export async function getOrders(id: string): Promise<Order[]> {
+export async function getOrders(id: any): Promise<any[]> {

// src/client.ts
-const handle = (payload: unknown): Order => {
+const handle = (payload: object): Order => {
```

## Author's comment

"I had to loosen the types a bit — the endpoint returns a slightly different shape and the build was red."

## Task

Your review verdict: approve, request changes, or block — and why. Is the build actually fixed, or is the failure being disabled?