<template>
  <div>
    <h1>{{ project_name }}</h1>
    <p>{{ description }}</p>
  </div>
</template>

<script setup lang="ts">
useHead({ title: '{{ project_name }}' })
</script>
