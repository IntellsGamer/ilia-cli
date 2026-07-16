import { Controller, Get } from '@nestjs/common'

@Controller()
export class AppController {
  @Get()
  root() {
    return { project: '{{ project_name }}', version: '{{ version }}' }
  }

  @Get('health')
  health() {
    return { status: 'ok' }
  }
}
