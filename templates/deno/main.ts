import { Application, Router } from 'oak'

const router = new Router()

router
  .get('/', (ctx) => {
    ctx.response.body = { project: '{{ project_name }}', version: '{{ version }}' }
  })
  .get('/health', (ctx) => {
    ctx.response.body = { status: 'ok' }
  })

const app = new Application()
app.use(router.routes())
app.use(router.allowedMethods())

console.log('{{ project_name }} running on http://localhost:{{ port }}')
await app.listen({ port: {{ port }} })
