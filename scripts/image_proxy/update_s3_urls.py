#!/usr/bin/env python3
"""
TSV 파일들의 thumbnail_url을 S3 URL로 업데이트하는 스크립트.

dataset_proper.tsv의 id → thumbnail_url 매핑을 사용하여
다른 TSV 파일들의 thumbnail_url을 S3 URL로 갱신합니다.
"""

import os
import csv
from pathlib import Path

def load_url_mapping(source_file: str) -> dict:
    """dataset_proper.tsv에서 item_id → thumbnail_urls 매핑을 로드합니다."""
    mapping = {}
    with open(source_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('item_id') and row.get('thumbnail_urls'):
                mapping[row['item_id']] = row['thumbnail_urls']
    return mapping

def update_tsv_file(file_path: str, url_mapping: dict) -> tuple:
    """TSV 파일의 thumbnail_urls를 업데이트합니다. (updated_count, total_count)를 반환합니다."""
    if not os.path.exists(file_path):
        return (0, 0)
    
    rows = []
    updated_count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        fieldnames = reader.fieldnames
        
        if 'thumbnail_urls' not in fieldnames:
            return (0, 0)
        
        for row in reader:
            row_id = row.get('item_id')
            if row_id and row_id in url_mapping:
                old_url = row.get('thumbnail_urls', '')
                new_url = url_mapping[row_id]
                if old_url != new_url:
                    row['thumbnail_urls'] = new_url
                    updated_count += 1
            rows.append(row)
    
    # 파일 다시 쓰기
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)
    
    return (updated_count, len(rows))

def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent.parent


def main():
    base_dir = get_project_root() / 'inputs'
    
    # 매핑 로드
    print("Loading URL mapping from dataset_proper.tsv...")
    url_mapping = load_url_mapping(base_dir / 'dataset_proper.tsv')
    print(f"Loaded {len(url_mapping)} URL mappings")
    
    # 업데이트할 파일 목록
    files_to_update = [
        base_dir / 'dataset_duplicated.tsv',
        base_dir / 'datasource_complete.tsv',
        base_dir / 'datasource_incomplete.tsv',
    ]
    
    # categories 폴더의 모든 TSV 파일 추가
    categories_dir = base_dir / 'categories'
    if categories_dir.exists():
        for tsv_file in categories_dir.glob('*.tsv'):
            files_to_update.append(tsv_file)
    
    # 각 파일 업데이트
    total_updated = 0
    for file_path in files_to_update:
        updated, total = update_tsv_file(str(file_path), url_mapping)
        if total > 0:
            print(f"Updated {file_path.name}: {updated}/{total} rows")
            total_updated += updated
        else:
            print(f"Skipped {file_path.name}: file not found or no thumbnail_url column")
    
    print(f"\nTotal updated: {total_updated} rows across all files")

if __name__ == '__main__':
    main()
