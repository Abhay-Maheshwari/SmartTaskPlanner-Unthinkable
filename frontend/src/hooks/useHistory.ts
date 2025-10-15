import { useEffect, useMemo, useState, useCallback } from 'react';
import { appendEvent, appendEvents, clearEvents, listEvents, type HistoryEvent, type HistoryEventType, type ListFilters } from '@/lib/history';

export interface HistoryFilters {
  types?: HistoryEventType[];
  taskId?: string | number;
  search?: string;
}

export function useHistory(initialFilters: HistoryFilters = {}) {
  const [filters, setFilters] = useState<HistoryFilters>(initialFilters);
  const [version, setVersion] = useState(0);

  const events = useMemo(() => {
    const lf: ListFilters = {
      types: filters.types,
      taskId: filters.taskId,
      search: filters.search,
    };
    return listEvents(lf);
  }, [filters, version]);

  useEffect(() => {
    const onChange = () => setVersion(v => v + 1);
    window.addEventListener('taskflow:history:changed', onChange as EventListener);
    window.addEventListener('storage', onChange);
    return () => {
      window.removeEventListener('taskflow:history:changed', onChange as EventListener);
      window.removeEventListener('storage', onChange);
    };
  }, []);

  const append = useCallback((event: HistoryEvent) => appendEvent(event), []);
  const appendMany = useCallback((events: HistoryEvent[]) => appendEvents(events), []);
  const clear = useCallback(() => clearEvents(), []);

  return { events, filters, setFilters, append, appendMany, clear };
}


