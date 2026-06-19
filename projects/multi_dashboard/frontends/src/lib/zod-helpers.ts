import { z } from 'zod'

export const nonEmptyString = z.string().trim().min(1)

// Normalize empty string to undefined so optional fields behave consistently.
export const optionalString = z
  .string()
  .optional()
  .transform((v) => (v === '' ? undefined : v))

export const positiveNumber = z.number().positive()

// Matches datetime-local input values: "2026-05-19T09:00"
export const datetimeLocal = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/, 'Invalid datetime')
