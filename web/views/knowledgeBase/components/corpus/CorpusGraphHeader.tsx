"use client";

import {
  Box,
  Maximize2,
  Minimize2,
  Search,
  Sun,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { SEARCH_COLOR_CONTAINS, SEARCH_COLOR_PREFIX } from "./constants";
import { GraphControlButton } from "./graph/GraphControlButton";
import type { useCorpusGraph } from "./useCorpusGraph";

type CorpusGraph = ReturnType<typeof useCorpusGraph>;

export function CorpusGraphHeader({
  graph,
  isFullscreen,
}: {
  graph: CorpusGraph;
  isFullscreen: boolean;
}) {
  const { t } = useTranslation();
  const {
    searchRef,
    isDark,
    setIsDark,
    is3D,
    setIs3D,
    searchQuery,
    setSearchQuery,
    searchOpen,
    setSearchOpen,
    searchMatches,
    trimmedSearch,
    focusSearchMatch,
    toggleFullscreen,
  } = graph;

  return (
    <header
      className={`flex flex-col gap-3 border-b px-4 py-4 sm:px-5 lg:flex-row lg:items-center lg:justify-between ${
        isDark
          ? "border-slate-700/80 bg-slate-900/90"
          : "border-slate-100 bg-white/80"
      }`}
    >
      <div className="shrink-0">
        <h2 className="text-lg font-bold tracking-tight sm:text-xl">
          {t("corpus.header.title")}
        </h2>
        <p
          className={`text-xs sm:text-sm ${isDark ? "text-slate-400" : "text-slate-500"}`}
        >
          {t("corpus.header.subtitle")}
        </p>
      </div>

      <div className="relative mx-auto w-full max-w-md flex-1 lg:mx-0">
        <Search
          className={`pointer-events-none absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 ${
            isDark ? "text-slate-500" : "text-slate-400"
          }`}
        />
        <input
          ref={searchRef}
          type="search"
          value={searchQuery}
          onChange={(event) => {
            setSearchQuery(event.target.value);
            setSearchOpen(true);
          }}
          onFocus={() => setSearchOpen(true)}
          onBlur={() => {
            window.setTimeout(() => setSearchOpen(false), 150);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && searchMatches[0]) {
              focusSearchMatch(searchMatches[0]);
            }
            if (event.key === "Escape") {
              setSearchQuery("");
              setSearchOpen(false);
            }
          }}
          placeholder={t("corpus.header.searchPlaceholder")}
          className={`w-full rounded-xl border py-2.5 pl-10 text-sm outline-none transition focus:ring-2 focus:ring-emerald-500/30 ${
            trimmedSearch ? "pr-24" : "pr-16"
          } ${
            isDark
              ? "border-slate-700 bg-slate-800 text-slate-100 placeholder:text-slate-500"
              : "border-slate-200 bg-slate-50 text-slate-900 placeholder:text-slate-400"
          }`}
        />
        {trimmedSearch ? (
          <span
            className={`pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded-md px-1.5 py-0.5 text-[10px] font-semibold ${
              searchMatches.length > 0
                ? isDark
                  ? "bg-amber-500/20 text-amber-300"
                  : "bg-amber-100 text-amber-800"
                : isDark
                  ? "bg-slate-700 text-slate-400"
                  : "bg-slate-200 text-slate-500"
            }`}
          >
            {t("corpus.header.resultsCount", { count: searchMatches.length })}
          </span>
        ) : (
          <kbd
            className={`pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded-md border px-1.5 py-0.5 text-[10px] font-medium sm:inline ${
              isDark
                ? "border-slate-600 bg-slate-800 text-slate-400"
                : "border-slate-200 bg-white text-slate-400"
            }`}
          >
            ⌘K
          </kbd>
        )}

        {searchOpen && trimmedSearch && (
          <div
            className={`absolute left-0 right-0 top-[calc(100%+6px)] z-30 max-h-64 overflow-y-auto rounded-xl border shadow-xl ${
              isDark
                ? "border-slate-700 bg-slate-900"
                : "border-slate-200 bg-white"
            }`}
          >
            {searchMatches.length === 0 ? (
              <p
                className={`px-4 py-3 text-sm ${
                  isDark ? "text-slate-400" : "text-slate-500"
                }`}
              >
                {t("corpus.header.noResults")}
              </p>
            ) : (
              searchMatches.map((match) => (
                <button
                  key={match.id}
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => focusSearchMatch(match)}
                  className={`flex w-full items-start gap-3 border-b px-4 py-2.5 text-left transition last:border-0 ${
                    isDark
                      ? "border-slate-800 hover:bg-slate-800"
                      : "border-slate-100 hover:bg-slate-50"
                  }`}
                >
                  <span
                    className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{
                      backgroundColor:
                        match.kind === "prefix"
                          ? SEARCH_COLOR_PREFIX
                          : SEARCH_COLOR_CONTAINS,
                    }}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-inherit">
                      {match.label}
                    </span>
                    <span
                      className={`mt-0.5 block text-[10px] font-semibold uppercase tracking-wide ${
                        isDark ? "text-slate-500" : "text-slate-400"
                      }`}
                    >
                      {match.nodeType}
                      {match.kind === "prefix"
                        ? t("corpus.header.matchPrefix")
                        : t("corpus.header.matchContains")}
                    </span>
                  </span>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      <div className="flex shrink-0 items-center justify-end gap-2">
        <GraphControlButton
          title={is3D ? t("corpus.header.mode2d") : t("corpus.header.mode3d")}
          onClick={() => setIs3D((prev) => !prev)}
          active={is3D}
        >
          <Box className="h-4 w-4" />
        </GraphControlButton>
        <GraphControlButton
          title={
            isFullscreen
              ? t("corpus.header.exitFullscreen")
              : t("corpus.header.fullscreen")
          }
          onClick={() => void toggleFullscreen()}
        >
          {isFullscreen ? (
            <Minimize2 className="h-4 w-4" />
          ) : (
            <Maximize2 className="h-4 w-4" />
          )}
        </GraphControlButton>
        <GraphControlButton
          title={
            isDark ? t("corpus.header.lightTheme") : t("corpus.header.darkTheme")
          }
          onClick={() => setIsDark((prev) => !prev)}
        >
          <Sun className="h-4 w-4" />
        </GraphControlButton>
      </div>
    </header>
  );
}
