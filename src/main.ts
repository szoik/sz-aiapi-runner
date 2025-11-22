import {NestFactory} from '@nestjs/core';
import {ValidationPipe, Logger} from '@nestjs/common';
import {SwaggerModule, DocumentBuilder} from '@nestjs/swagger';
import {SzOpenAITesterModule} from './sz-openai-tester.module';
import * as dotenv from 'dotenv';

dotenv.config();

async function bootstrap() {
  const logger = new Logger('Bootstrap');

  if (!process.env.OPENAI_API_KEY) {
    logger.error('❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다!');
    logger.error('💡 .env 파일에 OPENAI_API_KEY를 추가하거나 환경변수로 설정해주세요.');
    process.exit(1);
  }

  const app = await NestFactory.create(SzOpenAITesterModule, {
    logger: ['log', 'error', 'warn', 'debug', 'verbose'],
  });

  app.useGlobalPipes(
    new ValidationPipe({
      transform: true,
      whitelist: true,
    })
  );

  app.enableCors();

  const config = new DocumentBuilder()
    .setTitle('SZ-OpenAI Tester API')
    .setDescription('OpenAI HSCode/무게/부피 추정 테스트 도구')
    .setVersion('1.0')
    .addTag('SZ-Tools: OpenAI Tester')
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api-docs', app, document);

  const port = process.env.SZ_PORT || 3100;
  await app.listen(port);

  logger.log('');
  logger.log('========================================');
  logger.log(`🚀 SZ-OpenAI Tester 서버 시작됨!`);
  logger.log(`📡 서버 주소: http://localhost:${port}`);
  logger.log(`📚 Swagger 문서: http://localhost:${port}/api-docs`);
  logger.log(`🔑 OpenAI API Key: ${process.env.OPENAI_API_KEY ? '✅ 설정됨' : '❌ 미설정'}`);
  logger.log('========================================');
  logger.log('');
}

bootstrap();
