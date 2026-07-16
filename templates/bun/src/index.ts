import { Elysia } from 'elysia'

const app = new Elysia()
  .get('/', () => ({
    project: '{{ project_name }}',
    version: '{{ version }}',
    message: 'Hello from Bun + Elysia!',
  }))
  .get('/health', () => ({ status: 'ok' }))
  .listen({{ port }})

console.log(`{{ project_name }} running on http://localhost:{{ port }}`)
