import {IsString, IsNotEmpty, IsOptional} from 'class-validator';
import {ApiProperty} from '@nestjs/swagger';

export class ProductInfoRequestDto {
  @ApiProperty({
    description: '상품명',
    example: 'ワイヤレスマウス',
  })
  @IsString()
  @IsNotEmpty()
  productName: string;

  @ApiProperty({
    description: '카테고리',
    example: 'Electronics > Computer Accessories',
  })
  @IsString()
  @IsNotEmpty()
  category: string;

  @ApiProperty({
    description: '이미지 URL',
    example: 'https://example.com/image.jpg',
  })
  @IsString()
  @IsOptional()
  imageUrl?: string;
}
