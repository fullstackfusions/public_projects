import { type ReactNode } from 'react'
import { type FieldError } from 'react-hook-form'

interface FormFieldProps {
  label: string
  error?: FieldError
  required?: boolean
  className?: string
  children: ReactNode
}

export function FormField({ label, error, required, className = '', children }: FormFieldProps) {
  return (
    <label className={['flex flex-col gap-1 text-sm font-semibold text-slate-700', className].join(' ')}>
      <span>
        {label}
        {required && <span className="ml-0.5 text-rose-500">*</span>}
      </span>
      {children}
      {error && <p className="text-xs font-normal text-rose-600">{error.message}</p>}
    </label>
  )
}
