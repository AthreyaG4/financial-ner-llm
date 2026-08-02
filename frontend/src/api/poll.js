export async function pollUntil({ fn, isDone, intervalMs = 1000, timeoutMs = 30000 }) {
  const start = Date.now();
  while (true) {
    const result = await fn();
    if (isDone(result)) return result;
    if (Date.now() - start > timeoutMs) {
      throw new Error('Polling timed out');
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}
