import { invoke } from '@tauri-apps/api/core'

invoke('greet', { name: 'World' }).then(console.log)
