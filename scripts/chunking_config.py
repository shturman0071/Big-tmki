import os
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions, PdfFormatOption
from docling.chunking import HybridChunker
from typing import List, Dict, Any

# Загрузка конфига из переменных окружения
def get_config(key: str, default: any = None) -> any:
    """Получить значение из переменных окружения"""
    import os
    return os.getenv(key, default)

def get_chunker() -> HybridChunker:
    """
    Настроенный чанкер для технических документов
    Читает параметры из TMKI_CHUNK_* переменных
    """
    chunk_size = int(get_config("TMKI_CHUNK_SIZE", 1024))
    chunk_overlap = int(get_config("TMKI_CHUNK_OVERLAP", 128))
    split_by_headers = get_config("TMKI_CHUNK_SPLIT_BY_HEADERS", "true").lower() == "true"
    split_by_tables = get_config("TMKI_CHUNK_SPLIT_BY_TABLES", "false").lower() == "true"
    split_by_lists = get_config("TMKI_CHUNK_SPLIT_BY_LISTS", "false").lower() == "true"
    
    return HybridChunker(
        max_tokens=chunk_size,
        overlap_tokens=chunk_overlap,
        split_by_headers=split_by_headers,
        split_by_tables=split_by_tables,
        split_by_lists=split_by_lists,
    )

def get_converter() -> DocumentConverter:
    """
    Настроенный конвертер Docling для технических документов
    Включает OCR и извлечение таблиц
    """
    pipeline_opts = PdfPipelineOptions()
    pipeline_opts.do_ocr = True
    pipeline_opts.do_table_structure = True
    pipeline_opts.table_structure_options.do_cell_matching = True
    pipeline_opts.table_structure_options.do_merge_tables = True
    
    return DocumentConverter(
        format_options={
            "pdf": PdfFormatOption(
                pipeline_options=pipeline_opts,
                backend="pypdfium2"
            )
        }
    )

def process_document(filepath: str) -> List[Dict[str, Any]]:
    """
    Обработать документ и получить чанки с метаданными
    """
    converter = get_converter()
    chunker = get_chunker()
    result = converter.convert(filepath)
    chunks = []
    for chunk in chunker.chunk(result.document):
        chunk_data = {
            "text": chunk.text,
            "metadata": {
                "doc_id": os.path.basename(filepath),
                "doc_path": filepath,
                "page": getattr(chunk, "page", 0),
                "has_table": bool(getattr(chunk, "tables", [])),
                "section": getattr(chunk, "section_name", None),
            }
        }
        chunks.append(chunk_data)
    return chunks

def get_document_metadata(filepath: str) -> Dict[str, Any]:
    """Получить метаданные документа без полного чанкинга"""
    converter = get_converter()
    result = converter.convert(filepath)
    return {
        "doc_id": os.path.basename(filepath),
        "doc_path": filepath,
        "page_count": len(result.document.pages) if hasattr(result.document, "pages") else 0,
        "has_tables": bool(result.document.tables) if hasattr(result.document, "tables") else False,
        "has_images": bool(result.document.pictures) if hasattr(result.document, "pictures") else False,
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"Обработка: {test_file}")
        chunks = process_document(test_file)
        print(f"Получено чанков: {len(chunks)}")
        if chunks:
            print(f"Пример чанка:\n{chunks[0]['text'][:200]}...")
            print(f"Метаданные: {chunks[0]['metadata']}")
    else:
        print("Использование: python scripts/chunking_config.py <путь_к_файлу>")
