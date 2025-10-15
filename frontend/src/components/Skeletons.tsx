import { Card, CardContent } from "@/components/ui/card";

export const StatsSkeleton = () => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
    {Array.from({ length: 4 }).map((_, i) => (
      <Card key={i} className="bg-gradient-card/30 backdrop-blur-sm border-border">
        <CardContent className="p-6">
          <div className="h-5 w-24 bg-muted/40 rounded-md mb-3 animate-pulse"></div>
          <div className="h-8 w-32 bg-muted/40 rounded-md animate-pulse"></div>
        </CardContent>
      </Card>
    ))}
  </div>
);

export const ListSkeleton = () => (
  <div className="space-y-4">
    {Array.from({ length: 5 }).map((_, i) => (
      <Card key={i} className="bg-gradient-card/30 backdrop-blur-sm border-border">
        <CardContent className="p-6 space-y-3">
          <div className="h-6 w-1/3 bg-muted/40 rounded-md animate-pulse"></div>
          <div className="h-4 w-2/3 bg-muted/30 rounded-md animate-pulse"></div>
        </CardContent>
      </Card>
    ))}
  </div>
);


