'use strict';

/**
 * Lazy snapshot cache for the static site and the FastAPI preview.
 * A view calls load(), renders a loading message for null, then renders again
 * when onChange fires. Concurrent requests for the same file share one fetch.
 */
function createSnapshotStore(fetchFile, onChange) {
  const cache = new Map();
  const pending = new Map();
  let generation = 0;

  return {
    cache,
    load(file) {
      if (cache.has(file)) return cache.get(file);
      if (pending.has(file)) return null;

      const requestedGeneration = generation;
      const request = Promise.resolve()
        .then(() => fetchFile(file))
        .then((data) => {
          if (requestedGeneration === generation) cache.set(file, data);
        })
        .catch((error) => {
          if (requestedGeneration === generation) cache.set(file, { error: error.message });
        })
        .finally(() => {
          // Refresh starts a new generation. Old requests must never overwrite it.
          if (requestedGeneration !== generation) return;
          pending.delete(file);
          onChange();
        });

      pending.set(file, request);
      return null;
    },
    clear() {
      generation += 1;
      cache.clear();
      pending.clear();
    },
    isLoading() {
      return pending.size > 0;
    },
  };
}
