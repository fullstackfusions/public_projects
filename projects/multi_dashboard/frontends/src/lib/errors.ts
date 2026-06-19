export interface ErrorEnvelope {
  code: string
  message: string
  detail?: unknown
  trace_id?: string
}

export class ApiError extends Error {
  readonly code: string
  readonly detail?: unknown
  readonly trace_id?: string
  readonly status: number

  constructor(status: number, envelope: ErrorEnvelope) {
    super(envelope.message)
    this.name = 'ApiError'
    this.status = status
    this.code = envelope.code
    this.detail = envelope.detail
    this.trace_id = envelope.trace_id
  }

  static fromAxiosError(err: unknown): ApiError {
    const e = err as { response?: { status?: number; data?: ErrorEnvelope } }
    const status = e.response?.status ?? 0
    const data = e.response?.data
    if (data && typeof data === 'object' && 'code' in data && typeof data.code === 'string') {
      return new ApiError(status, data as ErrorEnvelope)
    }
    return new ApiError(status, {
      code: 'UNKNOWN',
      message: err instanceof Error ? err.message : 'An unexpected error occurred',
    })
  }
}
