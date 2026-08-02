import { apiFetch } from './client.js';
import { stageFromStatus } from './statusMap.js';

function mapExtraction(raw) {
  return {
    id: raw.id,
    fileName: raw.file_name,
    stage: stageFromStatus(raw.status),
    createdAt: raw.created_at,
    parsedText: raw.parsed_text ?? '',
    entities: raw.entities ?? [],
    elapsedLabel: raw.elapsed_label ?? '',
    errorMessage: raw.error_message ?? null,
  };
}

export async function createExtraction(file) {
  const form = new FormData();
  form.append('file', file);
  const raw = await apiFetch('/extractions', { method: 'POST', body: form });
  return mapExtraction(raw);
}

export async function getExtraction(id) {
  return mapExtraction(await apiFetch(`/extractions/${id}`));
}

export async function triggerExtraction(id) {
  return mapExtraction(await apiFetch(`/extractions/${id}/extract`, { method: 'POST' }));
}

export async function listExtractions() {
  const rows = await apiFetch('/extractions');
  return rows.map(mapExtraction);
}
