"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import { sankeyLinkHorizontal } from "d3-sankey";
import { useSankey } from "@/hooks/useSankey";
import type { SankeyData } from "@/types/pipeline";

interface SankeyDiagramProps {
  data: SankeyData;
  height?: number;
}

interface TooltipState {
  x: number;
  y: number;
  text: string;
  visible: boolean;
}

type SankeyNodeLike = {
  id: string;
  label: string;
  category: "policy" | "sector" | "effect" | "outcome";
  x0: number;
  x1: number;
  y0: number;
  y1: number;
};

type SankeyLinkLike = {
  source: SankeyNodeLike;
  target: SankeyNodeLike;
  value: number;
  width: number;
};

const CATEGORY_COLORS = {
  policy: "#F59E0B",
  sector: "#60A5FA",
  effect: "#2DD4BF",
  outcome: "#22C55E",
} as const;

export default function SankeyDiagram({ data, height = 320 }: SankeyDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipState>({ x: 0, y: 0, text: "", visible: false });
  const { width, graph } = useSankey(data, containerRef, height);

  const margin = useMemo(() => ({ top: 20, right: 160, bottom: 20, left: 160 }), []);
  const innerWidth = Math.max(0, width - margin.left - margin.right);

  useEffect(() => {
    if (!svgRef.current || !graph || width < 320) {
      return;
    }

    const nodes = graph.nodes as unknown as SankeyNodeLike[];
    const links = graph.links as unknown as SankeyLinkLike[];

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("width", width).attr("height", height);

    const root = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    const linkGroup = root.append("g").attr("class", "links");
    const nodeGroup = root.append("g").attr("class", "nodes");

    const getColor = (category: SankeyNodeLike["category"]) => CATEGORY_COLORS[category] ?? "#8A8880";

    const linkPath = sankeyLinkHorizontal<SankeyNodeLike, SankeyLinkLike>();

    const linkSelection = linkGroup
      .selectAll<SVGPathElement, SankeyLinkLike>("path")
      .data(links)
      .join("path")
      .attr("d", linkPath)
      .attr("fill", (d) => getColor(d.source.category))
      .attr("fill-opacity", 0.15)
      .attr("stroke", (d) => getColor(d.source.category))
      .attr("stroke-opacity", 0.4)
      .attr("stroke-width", (d) => Math.max(1, d.width ?? 1));

    linkSelection.each(function () {
      const path = this as SVGPathElement;
      const length = path.getTotalLength();
      d3.select(path).attr("stroke-dasharray", `${length} ${length}`).attr("stroke-dashoffset", length);
    });

    linkSelection
      .transition()
      .delay((_, i) => i * 80)
      .duration(800)
      .ease(d3.easeCubicOut)
      .attr("stroke-dashoffset", 0);

    const nodeSelection = nodeGroup
      .selectAll<SVGGElement, SankeyNodeLike>("g")
      .data(nodes)
      .join("g")
      .attr("transform", (d) => `translate(${d.x0},${d.y0})`)
      .attr("opacity", 0);

    nodeSelection
      .transition()
      .delay((_, i) => links.length * 80 + 200 + i * 30)
      .duration(220)
      .attr("opacity", 1);

    nodeSelection
      .append("rect")
      .attr("width", (d) => Math.max(18, d.x1 - d.x0))
      .attr("height", (d) => Math.max(6, d.y1 - d.y0))
      .attr("rx", 3)
      .attr("fill", (d) => getColor(d.category));

    nodeSelection
      .append("text")
      .attr("x", (d) => (d.x0 < innerWidth / 2 ? -10 : Math.max(18, d.x1 - d.x0) + 10))
      .attr("y", (d) => (d.y1 - d.y0) / 2)
      .attr("dy", "0.35em")
      .attr("text-anchor", (d) => (d.x0 < innerWidth / 2 ? "end" : "start"))
      .attr("fill", "#8A8880")
      .attr("font-size", "12px")
      .attr("font-family", "var(--font-mono), monospace")
      .text((d) => d.label);

    const connectedIds = (nodeId: string) => {
      const idSet = new Set<string>([nodeId]);
      links.forEach((link) => {
        if (link.source.id === nodeId || link.target.id === nodeId) {
          idSet.add(link.source.id);
          idSet.add(link.target.id);
        }
      });
      return idSet;
    };

    const getPoint = (event: MouseEvent) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) {
        return { x: event.clientX, y: event.clientY };
      }
      return { x: event.clientX - rect.left, y: event.clientY - rect.top };
    };

    linkSelection
      .on("mouseover", (event, link) => {
        const sourceId = link.source.id;
        const targetId = link.target.id;
        linkSelection.attr("opacity", (d) => (d.source.id === sourceId && d.target.id === targetId ? 1 : 0.15));
        nodeSelection.attr("opacity", (d) => (d.id === sourceId || d.id === targetId ? 1 : 0.15));
        const point = getPoint(event as MouseEvent);
        setTooltip({
          visible: true,
          x: point.x + 12,
          y: point.y - 12,
          text: `${link.source.label} -> ${link.target.label}: ${link.value}`,
        });
      })
      .on("mousemove", (event) => {
        const point = getPoint(event as MouseEvent);
        setTooltip((prev) => ({ ...prev, x: point.x + 12, y: point.y - 12 }));
      })
      .on("mouseout", () => {
        linkSelection.attr("opacity", 1);
        nodeSelection.attr("opacity", 1);
        setTooltip((prev) => ({ ...prev, visible: false }));
      });

    nodeSelection
      .on("mouseover", (event, node) => {
        const ids = connectedIds(node.id);
        linkSelection.attr("opacity", (link) => (ids.has(link.source.id) && ids.has(link.target.id) ? 1 : 0.15));
        nodeSelection.attr("opacity", (d) => (ids.has(d.id) ? 1 : 0.15));
        const totalFlow = links
          .filter((link) => link.source.id === node.id || link.target.id === node.id)
          .reduce((sum, link) => sum + link.value, 0);
        const point = getPoint(event as MouseEvent);
        setTooltip({
          visible: true,
          x: point.x + 12,
          y: point.y - 12,
          text: `${node.label} · flow ${Math.round(totalFlow)}`,
        });
      })
      .on("mousemove", (event) => {
        const point = getPoint(event as MouseEvent);
        setTooltip((prev) => ({ ...prev, x: point.x + 12, y: point.y - 12 }));
      })
      .on("mouseout", () => {
        linkSelection.attr("opacity", 1);
        nodeSelection.attr("opacity", 1);
        setTooltip((prev) => ({ ...prev, visible: false }));
      });
  }, [graph, height, innerWidth, margin.left, margin.top, width]);

  return (
    <div ref={containerRef} className="relative w-full overflow-x-auto">
      <svg ref={svgRef} className="w-full" style={{ height }} role="img" aria-label="Economic impact Sankey diagram" />
      {tooltip.visible && (
        <div
          className="pointer-events-none absolute z-20 rounded border border-white/15 bg-black/85 px-2 py-1 text-[11px] text-white/75"
          style={{ left: tooltip.x, top: tooltip.y, fontFamily: "var(--font-mono), monospace" }}
        >
          {tooltip.text}
        </div>
      )}
    </div>
  );
}
