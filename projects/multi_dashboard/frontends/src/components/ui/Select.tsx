import { forwardRef, type SelectHTMLAttributes } from 'react'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  error?: string
  options: { value: string | number; label: string }[]
  placeholder?: string
}

const baseClass =
  'w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm shadow-sm transition focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/40'
const errorClass = 'border-rose-400 focus:border-rose-500 focus:ring-rose-300/40'

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ error, options, placeholder, className = '', ...rest }, ref) => (
    <div className="flex flex-col gap-1">
      <select
        ref={ref}
        className={[baseClass, error ? errorClass : '', className].join(' ')}
        {...rest}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error && <p className="text-xs text-rose-600">{error}</p>}
    </div>
  ),
)
Select.displayName = 'Select'
