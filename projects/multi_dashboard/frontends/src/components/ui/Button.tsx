import { type ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  loading?: boolean
}

const variantClass: Record<Variant, string> = {
  primary:
    'bg-brand text-white hover:bg-brand-dark focus:ring-brand/40',
  secondary:
    'bg-slate-100 text-slate-700 hover:bg-slate-200 focus:ring-slate-300',
  danger:
    'bg-rose-600 text-white hover:bg-rose-500 focus:ring-rose-300',
  ghost:
    'bg-transparent text-slate-700 hover:bg-slate-100 focus:ring-slate-300',
}

export function Button({ variant = 'primary', loading, children, className = '', disabled, ...rest }: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled ?? loading}
      className={[
        'inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold transition',
        'focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-70',
        variantClass[variant],
        className,
      ].join(' ')}
    >
      {loading ? <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> : null}
      {children}
    </button>
  )
}
