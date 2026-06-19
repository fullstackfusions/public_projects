import { useEffect } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  Box,
  Typography,
  Paper,
  TextField,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Button,
  Alert,
  CircularProgress,
  Divider,
  Chip,
} from '@mui/material'
import NotificationsIcon from '@mui/icons-material/Notifications'
import EmailIcon from '@mui/icons-material/Email'
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid'
import WhatsAppIcon from '@mui/icons-material/WhatsApp'
import { UpdatePreferenceSchema } from './schemas'
import type { UpdatePreference, Channel } from './types'
import { useMyPreferences, useUpdatePreferences } from './hooks'

const CHANNEL_INFO: Record<Channel, { label: string; icon: React.ReactNode; hint: string }> = {
  email: {
    label: 'Email',
    icon: <EmailIcon fontSize="small" />,
    hint: 'Receive HTML email reminders via Mailpit (local) or your SMTP server.',
  },
  push: {
    label: 'Push (ntfy)',
    icon: <PhoneAndroidIcon fontSize="small" />,
    hint: 'Install the ntfy app and subscribe to your personal topic for push notifications.',
  },
  whatsapp: {
    label: 'WhatsApp',
    icon: <WhatsAppIcon fontSize="small" />,
    hint: 'Receive messages via WAHA self-hosted WhatsApp gateway. Provide E.164 phone number.',
  },
}

export function PreferencesPage() {
  const { data: prefs, isLoading, isError } = useMyPreferences()
  const { mutate: update, isPending: isSaving, isSuccess, isError: isSaveError } = useUpdatePreferences()

  const { control, handleSubmit, reset, watch } = useForm<UpdatePreference>({
    resolver: zodResolver(UpdatePreferenceSchema),
    defaultValues: {
      email: null,
      phone: null,
      ntfy_topic: null,
      enabled_channels: [],
    },
  })

  // Populate form once preferences load
  useEffect(() => {
    if (prefs) {
      reset({
        email: prefs.email ?? null,
        phone: prefs.phone ?? null,
        ntfy_topic: prefs.ntfy_topic ?? null,
        enabled_channels: prefs.enabled_channels as Channel[],
      })
    }
  }, [prefs, reset])

  const enabledChannels = watch('enabled_channels') ?? []

  const toggleChannel = (
    channel: Channel,
    current: Channel[],
    onChange: (v: Channel[]) => void,
  ) => {
    if (current.includes(channel)) {
      onChange(current.filter((c) => c !== channel))
    } else {
      onChange([...current, channel])
    }
  }

  const onSubmit = (values: UpdatePreference) => {
    update(values)
  }

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" mt={8}>
        <CircularProgress />
      </Box>
    )
  }

  if (isError) {
    return (
      <Box maxWidth={600} mx="auto" mt={4}>
        <Alert severity="error">Failed to load preferences. Is the notification service running?</Alert>
      </Box>
    )
  }

  return (
    <Box maxWidth={620} mx="auto" py={4} px={2}>
      {/* Header */}
      <Box display="flex" alignItems="center" gap={1.5} mb={3}>
        <NotificationsIcon color="primary" fontSize="large" />
        <Box>
          <Typography variant="h5" fontWeight={700}>
            Notification Preferences
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Choose which channels you'd like to receive tax filing reminders on.
          </Typography>
        </Box>
      </Box>

      <form onSubmit={handleSubmit(onSubmit)}>
        {/* Channel toggles */}
        <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
          <Typography variant="subtitle1" fontWeight={600} mb={2}>
            Enabled Channels
          </Typography>
          <Controller
            name="enabled_channels"
            control={control}
            render={({ field }) => (
              <FormGroup>
                {(Object.entries(CHANNEL_INFO) as [Channel, typeof CHANNEL_INFO[Channel]][]).map(
                  ([ch, info]) => (
                    <Box key={ch} mb={1.5}>
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={field.value?.includes(ch) ?? false}
                            onChange={() =>
                              toggleChannel(ch, field.value ?? [], field.onChange)
                            }
                          />
                        }
                        label={
                          <Box display="flex" alignItems="center" gap={1}>
                            {info.icon}
                            <span>{info.label}</span>
                            {field.value?.includes(ch) && (
                              <Chip label="enabled" size="small" color="success" />
                            )}
                          </Box>
                        }
                      />
                      <Typography variant="caption" color="text.secondary" ml={4}>
                        {info.hint}
                      </Typography>
                    </Box>
                  ),
                )}
              </FormGroup>
            )}
          />
        </Paper>

        {/* Address fields */}
        <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
          <Typography variant="subtitle1" fontWeight={600} mb={2}>
            Recipient Addresses
          </Typography>

          <Controller
            name="email"
            control={control}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                value={field.value ?? ''}
                onChange={(e) => field.onChange(e.target.value || null)}
                label="Email address"
                type="email"
                fullWidth
                size="small"
                sx={{ mb: 2 }}
                disabled={!enabledChannels.includes('email')}
                error={!!fieldState.error}
                helperText={
                  fieldState.error?.message ??
                  (enabledChannels.includes('email') ? 'Required when email channel is enabled.' : '')
                }
              />
            )}
          />

          <Controller
            name="ntfy_topic"
            control={control}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                value={field.value ?? ''}
                onChange={(e) => field.onChange(e.target.value || null)}
                label="ntfy topic"
                fullWidth
                size="small"
                sx={{ mb: 2 }}
                disabled={!enabledChannels.includes('push')}
                error={!!fieldState.error}
                helperText={
                  fieldState.error?.message ??
                  'Your private ntfy topic name, e.g. "mihir-tax-reminders".'
                }
              />
            )}
          />

          <Controller
            name="phone"
            control={control}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                value={field.value ?? ''}
                onChange={(e) => field.onChange(e.target.value || null)}
                label="WhatsApp phone number (E.164)"
                fullWidth
                size="small"
                disabled={!enabledChannels.includes('whatsapp')}
                error={!!fieldState.error}
                helperText={
                  fieldState.error?.message ?? 'Include country code, e.g. +14155552671'
                }
              />
            )}
          />
        </Paper>

        {/* Status alerts */}
        {isSuccess && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Preferences saved successfully.
          </Alert>
        )}
        {isSaveError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to save preferences. Please try again.
          </Alert>
        )}

        <Divider sx={{ mb: 2 }} />

        <Button
          type="submit"
          variant="contained"
          disabled={isSaving}
          startIcon={isSaving ? <CircularProgress size={16} /> : null}
        >
          {isSaving ? 'Saving…' : 'Save Preferences'}
        </Button>
      </form>
    </Box>
  )
}

export default PreferencesPage
