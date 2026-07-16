import { NestFactory } from '@nestjs/core'
import { AppModule } from './app.module'

async function bootstrap() {
  const app = await NestFactory.create(AppModule)
  app.enableCors()
  await app.listen({{ port }})
  console.log('{{ project_name }} running on http://localhost:{{ port }}')
}
bootstrap()
