import Shell from './components/Shell'
import { usePath } from './lib/nav'
import Overview from './pages/Overview'
import SessionPage from './pages/SessionPage'

export default function App() {
  const path = usePath()
  const session = path.match(/^\/session\/(.+)$/)
  return <Shell>{session ? <SessionPage key={session[1]} id={decodeURIComponent(session[1])} /> : <Overview />}</Shell>
}
