import { initTRPC } from '@trpc/server'
import superjson from 'superjson'
import { z } from 'zod'

const t = initTRPC.create({ transformer: superjson })

export const router = t.router
export const publicProcedure = t.procedure

export const appRouter = router({
  hello: publicProcedure
    .input(z.object({ name: z.string().default('world') }))
    .query(({ input }) => `Hello, ${input.name}!`),
  version: publicProcedure
    .query(() => '{{ version }}'),
})

export type AppRouter = typeof appRouter
