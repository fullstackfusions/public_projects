export function useAuthToken(): string | null {
  return localStorage.getItem('access_token')
}
