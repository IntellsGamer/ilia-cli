import { Links, Meta, Outlet, Scripts } from '@remix-run/react'

export default function Root() {
  return (
    <html lang="en">
      <head>
        <Meta />
        <Links />
        <title>{{ project_name }}</title>
      </head>
      <body>
        <Outlet />
        <Scripts />
      </body>
    </html>
  )
}
