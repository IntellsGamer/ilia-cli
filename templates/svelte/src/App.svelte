<script>
  let name = $state('world')
</script>

<h1>{{ project_name }}</h1>
<p>{{ description }}</p>
<input bind:value={name} placeholder="Your name" />
<p>Hello, {name}!</p>

<style>
  h1 { color: #ff3e00; }
</style>
