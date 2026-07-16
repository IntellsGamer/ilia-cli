import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { logger } from 'hono/logger'

const app = new Hono()

app.use('*', cors())
app.use('*', logger())

app.get('/', (c) => c.json({
  project: '{{ project_name }}',
  version: '{{ version }}',
  message: 'Hello from Hono!'
}))

app.get('/health', (c) => c.json({ status: 'ok' }))

export default {
  port: {{ port }},
  fetch: app.fetch,
}
