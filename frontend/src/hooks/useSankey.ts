import { RefObject, useEffect, useMemo, useState } from "react";
import { sankey, sankeyLeft, type SankeyGraph } from "d3-sankey";
import type { SankeyData } from "@/types/pipeline";

export interface SankeyLayoutResult {
  width: number;
  graph: SankeyGraph<Record<string, unknown>, Record<string, unknown>> | null;
}

export function useSankey(
  data: SankeyData | null,
  containerRef: RefObject<HTMLDivElement | null>,
  height: number,
): SankeyLayoutResult {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      const nextWidth = entries[0]?.contentRect.width ?? 0;
      setWidth(Math.max(0, Math.floor(nextWidth)));
    });

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [containerRef]);

  const graph = useMemo(() => {
    if (!data || data.nodes.length < 2 || data.links.length < 1 || width < 320) {
      return null;
    }

    const margin = { top: 20, right: 160, bottom: 20, left: 160 };
    const innerWidth = Math.max(280, width - margin.left - margin.right);
    const innerHeight = Math.max(120, height - margin.top - margin.bottom);

    const nodeMap = new Map(data.nodes.map((node, index) => [node.id, index]));
    const nodes = data.nodes.map((node) => ({ ...node }));
    const links = data.links
      .filter((link) => nodeMap.has(link.source) && nodeMap.has(link.target))
      .map((link) => ({
        source: nodeMap.get(link.source) ?? 0,
        target: nodeMap.get(link.target) ?? 0,
        value: link.value,
        label: link.label,
      }));

    if (!links.length) {
      return null;
    }

    return sankey<Record<string, unknown>, Record<string, unknown>>()
      .nodeWidth(18)
      .nodePadding(24)
      .nodeAlign(sankeyLeft)
      .extent([
        [0, 0],
        [innerWidth, innerHeight],
      ])({
        nodes,
        links,
      });
  }, [data, height, width]);

  return { width, graph };
}
