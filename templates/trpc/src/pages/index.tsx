import { trpc } from '../utils/trpc'

export default function Home() {
  const hello = trpc.hello.useQuery({ name: 'world' })
  const version = trpc.version.useQuery()

  return (
    <div>
      <h1>{{ project_name }}</h1>
      <p>{{ description }}</p>
      <p>Message: {hello.data ?? 'Loading...'}</p>
      <p>Version: {version.data ?? '...'}</p>
    </div>
  )
}
