import Fastify from 'fastify'
import cors from '@fastify/cors'

const app = Fastify({ logger: true })

await app.register(cors)

app.get('/', async () => ({
  project: '{{ project_name }}',
  version: '{{ version }}',
}))

app.get('/health', async () => ({ status: 'ok' }))

const start = async () => {
  try {
    await app.listen({ port: {{ port }}, host: '0.0.0.0' })
    console.log('{{ project_name }} running on http://localhost:{{ port }}')
  } catch (err) {
    app.log.error(err)
    process.exit(1)
  }
}
start()
