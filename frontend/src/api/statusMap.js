export const STATUS_TO_STAGE = {
  parsing: 'parsingDoc',
  parsed: 'parsed',
  parse_failed: 'errorParse',
  extracting: 'loading',
  extracted: 'results',
  extract_failed: 'errorExtract',
};

export const stageFromStatus = (status) => STATUS_TO_STAGE[status] ?? 'upload';
