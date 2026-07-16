import Head from 'next/head'

export default function Home() {
  return (
    <>
      <Head>
        <title>{{ project_name }}</title>
        <meta name="description" content="{{ description }}" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <main>
        <h1>Welcome to {{ project_name }}</h1>
        <p>{{ description }}</p>
      </main>
    </>
  )
}
