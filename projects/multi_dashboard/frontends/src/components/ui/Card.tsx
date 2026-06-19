import { type ReactNode } from 'react'

interface CardProps {
  title?: string
  children: ReactNode
  className?: string
}

export function Card({ title, children, className = '' }: CardProps) {
  return (
    <div className={['space-y-4 rounded-2xl bg-white p-6 shadow-card', className].join(' ')}>
      {title && <h2 className="text-xl font-semibold text-slate-900">{title}</h2>}
      {children}
    </div>
  )
}
