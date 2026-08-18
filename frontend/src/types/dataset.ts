export interface AnnotationType {
  extension: string;
  description: string;
}

export interface DatasetEntry {
  id: string;
  name: string;
  short_description: string;
  source: string;
  source_url: string;
  doi?: string;
  version: string;
  published?: string;
  license: string;
  citation: string;
  num_records: number;
  record_names: string[];
  signals_summary: string;
  annotation_types: AnnotationType[];
  recommended_use?: string;
  ingestion_status: "cataloged" | "downloading" | "ingested" | "error";
  checksum: string | null;
  download_date: string | null;
}
