import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render } from '../../../test-utils/render'
import { SchedulerPage } from '../SchedulerPage'

// Pin time to match fixture events (2026-05-19)
const FIXED_DATE = new Date('2026-05-19T08:00:00.000Z')

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(FIXED_DATE)
})

afterEach(() => {
  vi.useRealTimers()
})

describe('SchedulerPage', () => {
  it('renders the page headings', () => {
    render(<SchedulerPage />)
    expect(screen.getByText('Create Event')).toBeInTheDocument()
  })

  it('loads and displays events for the selected date', async () => {
    vi.useRealTimers() // real timers needed for async resolution
    render(<SchedulerPage />)

    // Loading state shows first
    expect(screen.getByText(/loading events/i)).toBeInTheDocument()

    // Events appear after fetch resolves
    await waitFor(() => {
      expect(screen.getByText('Team standup')).toBeInTheDocument()
    })
    expect(screen.getByText('Lunch with client')).toBeInTheDocument()
  })

  it('switches form heading to "Edit Event" when an edit button is clicked', async () => {
    vi.useRealTimers()
    const user = userEvent.setup()
    render(<SchedulerPage />)

    await waitFor(() => screen.getByText('Team standup'))

    const editButtons = screen.getAllByRole('button', { name: /edit/i })
    await user.click(editButtons[0])

    expect(screen.getByText('Edit Event')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /update event/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('shows validation error when form is submitted empty', async () => {
    vi.useRealTimers()
    const user = userEvent.setup()
    render(<SchedulerPage />)

    // Clear the title field and submit
    const titleInput = screen.getByRole('textbox', { name: /title/i })
    await user.clear(titleInput)
    await user.click(screen.getByRole('button', { name: /add event/i }))

    await waitFor(() => {
      expect(screen.getByText(/title is required/i)).toBeInTheDocument()
    })
  })
})
