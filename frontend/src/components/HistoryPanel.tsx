import { useEffect, useMemo, useState } from 'react';
import { X, Trash2, Download, Filter, Search, Clock, FolderPlus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useHistory } from '@/hooks/useHistory';
import { HistoryEventType } from '@/lib/history';

const typeColors: Record<HistoryEventType, string> = {
  'plan.created': 'bg-accent/10 text-accent',
  'task.created': 'bg-success/10 text-success',
  'task.updated': 'bg-primary/10 text-primary',
  'task.deleted': 'bg-destructive/10 text-destructive',
  'task.status': 'bg-warning/10 text-warning',
};

export const HistoryPanel = () => {
  const [open, setOpen] = useState(false);
  const { events, filters, setFilters, clear } = useHistory({ types: ['plan.created'] });

  useEffect(() => {
    const onToggle = () => setOpen(v => !v);
    window.addEventListener('taskflow:history:toggle', onToggle);
    return () => window.removeEventListener('taskflow:history:toggle', onToggle);
  }, []);

  const grouped = useMemo(() => {
    // Group by batchId, with undefined in its own group
    const map = new Map<string, typeof events>();
    for (const e of events) {
      const key = e.batchId || `single-${e.id}`;
      const arr = map.get(key) || [];
      arr.push(e);
      map.set(key, arr);
    }
    return Array.from(map.entries());
  }, [events]);

  const exportJson = () => {
    const dataStr = JSON.stringify(events, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `task-history-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex">
      <div className="flex-1" onClick={() => setOpen(false)} />
      <div className="w-full sm:w-[520px] h-full bg-background border-l border-border/50 shadow-2xl animate-slide-in-right">
        <Card className="h-full rounded-none border-0">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border/50">
            <div className="space-y-1">
              <CardTitle className="text-xl font-bold">History</CardTitle>
              <div className="text-xs text-muted-foreground">Local to this browser</div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon" onClick={exportJson} title="Export JSON">
                <Download className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon" onClick={() => clear()} title="Clear history">
                <Trash2 className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" onClick={() => setOpen(false)}>
                <X className="h-5 w-5" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search summaries..."
                  className="pl-8"
                  value={filters.search || ''}
                  onChange={(e) => setFilters(f => ({ ...f, search: e.target.value }))}
                />
              </div>
              <Select
                value={(filters.types && filters.types[0]) || 'all'}
                onValueChange={(v) => {
                  if (v === 'all') setFilters(f => ({ ...f, types: undefined }));
                  else setFilters(f => ({ ...f, types: [v as HistoryEventType] }));
                }}
              >
                <SelectTrigger className="w-40">
                  <Filter className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All types</SelectItem>
                  <SelectItem value="plan.created">Plan created</SelectItem>
                  <SelectItem value="task.created">Task created</SelectItem>
                  <SelectItem value="task.updated">Task updated</SelectItem>
                  <SelectItem value="task.status">Status changed</SelectItem>
                  <SelectItem value="task.deleted">Task deleted</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-4 max-h-[calc(100vh-200px)] overflow-auto pr-2">
              {grouped.length === 0 && (
                <div className="text-sm text-muted-foreground">No history yet. Perform some actions to see them here.</div>
              )}
              {grouped.map(([groupId, group]) => (
                <div key={groupId} className="border border-border/50 rounded-lg overflow-hidden">
                  <div className="px-4 py-2 bg-muted/40 border-b border-border/50 text-xs text-muted-foreground">
                    {group[0].batchId ? `Batch ${group[0].batchId}` : 'Single event'}
                  </div>
                  <div className="divide-y divide-border/50">
                    {group.map(e => (
                      <div
                        key={e.id}
                        className={`p-3 flex items-start gap-3 ${e.type === 'plan.created' ? 'cursor-pointer hover:bg-secondary/30' : ''}`}
                        onClick={() => {
                          if (e.type === 'plan.created' && e.plan) {
                            window.dispatchEvent(new CustomEvent('taskflow:history:open-plan', { detail: { plan: e.plan } }));
                          }
                        }}
                      >
                        <Badge className={`${typeColors[e.type]} text-xs`}>{e.type.replace('task.', '').replace('plan.', 'plan ')}</Badge>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-foreground truncate flex items-center gap-2">
                            {e.type === 'plan.created' && <FolderPlus className="h-3.5 w-3.5 text-accent" />}
                            <span>{e.summary}</span>
                          </div>
                          <div className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                            <Clock className="h-3 w-3" /> {new Date(e.timestamp).toLocaleString()}
                            {e.type !== 'plan.created' && (
                              <span className="ml-2 opacity-70">• Task {String(e.taskId)}</span>
                            )}
                          </div>
                          {(e.before || e.after) && (
                            <details className="mt-2">
                              <summary className="text-xs cursor-pointer text-muted-foreground">Details</summary>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                                {e.before && (
                                  <pre className="text-xs bg-secondary/30 p-2 rounded border border-border/50 overflow-auto max-h-40">{JSON.stringify(e.before, null, 2)}</pre>
                                )}
                                {e.after && (
                                  <pre className="text-xs bg-secondary/30 p-2 rounded border border-border/50 overflow-auto max-h-40">{JSON.stringify(e.after, null, 2)}</pre>
                                )}
                              </div>
                            </details>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};


