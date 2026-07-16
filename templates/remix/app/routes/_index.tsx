import type { MetaFunction } from '@remix-run/node'

export const meta: MetaFunction = () => [
  { title: '{{ project_name }}' },
  { name: 'description', content: '{{ description }}' },
]

export default function Index() {
  return (
    <div>
      <h1>{{ project_name }}</h1>
      <p>{{ description }}</p>
    </div>
  )
}
