import { useState } from 'preact/hooks'

export default function App() {
  const [name, setName] = useState('world')
  return (
    <div>
      <h1>{{ project_name }}</h1>
      <p>{{ description }}</p>
      <input value={name} onInput={e => setName(e.target.value)} />
      <p>Hello, {name}!</p>
    </div>
  )
}
