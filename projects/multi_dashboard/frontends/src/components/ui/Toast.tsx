import { Alert, Snackbar } from '@mui/material'

type Severity = 'success' | 'error' | 'warning' | 'info'

interface ToastProps {
  open: boolean
  message: string
  severity?: Severity
  duration?: number
  onClose: () => void
}

export function Toast({ open, message, severity = 'info', duration = 4000, onClose }: ToastProps) {
  return (
    <Snackbar
      open={open}
      autoHideDuration={duration}
      onClose={onClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
    >
      <Alert onClose={onClose} severity={severity} variant="filled" sx={{ width: '100%' }}>
        {message}
      </Alert>
    </Snackbar>
  )
}
