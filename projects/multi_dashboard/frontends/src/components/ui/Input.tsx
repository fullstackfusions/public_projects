import { forwardRef, type InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string
}

const baseClass =
  'w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm shadow-sm transition focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/40'
const errorClass = 'border-rose-400 focus:border-rose-500 focus:ring-rose-300/40'

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ error, className = '', ...rest }, ref) => (
    <div className="flex flex-col gap-1">
      <input
        ref={ref}
        className={[baseClass, error ? errorClass : '', className].join(' ')}
        {...rest}
      />
      {error && <p className="text-xs text-rose-600">{error}</p>}
    </div>
  ),
)
Input.displayName = 'Input'
