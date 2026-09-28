import Shell from './components/Shell'
import { usePath } from './lib/nav'
import Judges from './pages/Judges'
import Overview from './pages/Overview'
import SessionPage from './pages/SessionPage'

export default function App() {
  const path = usePath()
  const session = path.match(/^\/session\/(.+)$/)
  const judges = !session && path.replace(/\/$/, '') === '/judges'
  const page = session ? (
    <SessionPage key={session[1]} id={decodeURIComponent(session[1])} />
  ) : judges ? (
    <Judges />
  ) : (
    <Overview />
  )
  return <Shell onJudges={judges}>{page}</Shell>
}
