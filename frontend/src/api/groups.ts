export type Group = {
  id: number;
  parent_id: number | null;
  name: string;
  level: number;
  sort_order?: number;
};

export function buildGroupPaths(groups: Group[] | undefined): Record<number, string> {
  const map: Record<number, string> = {};
  if (!groups) return map;
  const byId = Object.fromEntries(groups.map((g) => [g.id, g]));
  for (const g of groups) {
    const parts: string[] = [];
    let cur: Group | undefined = g;
    while (cur) {
      parts.unshift(cur.name);
      cur = cur.parent_id ? byId[cur.parent_id] : undefined;
    }
    map[g.id] = parts.join(" / ");
  }
  return map;
}
