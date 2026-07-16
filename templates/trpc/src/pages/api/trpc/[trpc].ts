import { fetchRequestHandler } from '@trpc/server/adapters/fetch'
import { appRouter } from '../../../server/trpc'

export default async function handler(req: Request) {
  return fetchRequestHandler({
    endpoint: '/api/trpc',
    req,
    router: appRouter,
    createContext: () => ({}),
  })
}
