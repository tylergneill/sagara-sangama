.PHONY: serve-fulltext serve-all serve-all-fulltext counts growth search data logo scroll serve free-server-port \
        get-server-ip-address serve-all serve-one free-all-server-ports status \
        ws-dump ws-process ws-backfill ws-changelog ws-audit \
        ebs-clearance ebs-fetch-metadata ebs-parse-metadata ebs-fetch-text ebs-count-sizes ebs-build ebs-changelog ebs-audit \
        sd-fetch-metadata sd-build-catalogue sd-fetch-text sd-parse-site sd-parse-listings sd-count-sizes sd-build sd-changelog sd-audit \
        steps

# ============================================================================
# GROUP 1 -- build the page's inputs.
# ============================================================================
# This repo holds no corpus of its own. It sums over the three Atlases, which
# live beside it at ../atlases/ and are read but never written to.
#
# **There is no target here that refreshes an Atlas, on purpose.** Each is
# refreshed by its own Makefile, in its own vocabulary, and the costs are not
# comparable -- wikisource pulls a monthly dump in minutes, while the other two
# crawl for 5.4h and 6.5h at one request per 2s. A single "rebuild everything"
# recipe would hide that, and would break the rule this layer is built on: it
# reads each Atlas's PUBLISHED docs/data/ and nothing else (see CONTRACT.md).
# So `make data` below assumes the Atlases have already been rebuilt.
#
# The map of what each one costs is in README.md, under "Maintaining the
# Atlases".

# Read each Atlas's docs/data/tree.json -> docs/data/counts.json, the figures
# the home page typesets. Uses `all_stats.text_count`, the one field that means
# the same thing in all three (`count` includes category nodes, so it is mostly
# structure for wikisource). No network; re-run after any Atlas re-ingests.
# Override the Atlas location with `make counts ARGS="--atlas-root /path"`.
#   make counts
#   make counts ARGS="--print"               # show the table
counts:
	python collect_atlas_counts.py $(ARGS)

# Read each Atlas's docs/data/changelog.json -> docs/data/growth.json, the
# series the About page's chart plots. Cumulative texts and IAST bytes, each
# Atlas in its own periodicity (wikisource monthly, the other two yearly) --
# they are plotted against a real time axis rather than resampled onto a shared
# grid. Same boundary as `counts`: published docs/data only, no network.
#   make growth
#   make growth ARGS="--print"               # show the series
growth:
	python collect_atlas_growth.py $(ARGS)

# Read each Atlas's docs/data/tree.json -> docs/data/search.json, the index
# docs/search.html searches. One record per work: title, size, date and the
# per-item links that Atlas offers, with ids rather than URLs so the file stays
# ~8 MB (1.2 MB gzipped) instead of 18. Same boundary as the two above.
#
# It reconciles its own walks against each Atlas's published text_count and
# FAILS if one drifts -- an Atlas that reorganises its tree should break this
# loudly rather than quietly indexing half a collection. E-bhāratīsampat is the
# one expected excess: it also catalogues PDF-only scans, which are indexed,
# flagged, and hidden in the UI until asked for.
#   make search
#   make search ARGS="--print"               # show the per-Atlas table
search:
	python collect_atlas_search.py $(ARGS)

# All three, which is what a re-read of the Atlases means in practice.
data: counts growth search

# Write docs/assets/logo.svg (page) and favicon.svg (tab). Both are generated
# at their own size rather than one scaled twice, so the small one keeps the
# thicker ring the script gives it. The HTML points at these two names.
#
#   N      petal count           5 (one per Atlas; was 3 until 2026-10)
#   K      petal fatness         0.45, must stay under sin(pi/N); at 5 drops
#                                0.5 closes the gaps and reads as a flower
#   STYLE  ring | gapped-ring | bindu | ring+bindu | gapped-ring+bindu
#            ring         struck across the petals
#            gapped-ring  floats in a cleared band
#            bindu        centre dot only, no ring
#            +bindu       adds the dot to a ring style (wants K >= 0.48)
#
#   make logo STYLE=bindu
#   make logo N=4 K=0.55 STYLE=ring+bindu
N ?= 5
K ?= 0.52
STYLE ?= bindu
LOGO_SIZE ?= 512
FAVICON_SIZE ?= 24

logo:
	@python generate_logo.py --n $(N) --k $(K) --style $(STYLE) \
	    --sizes $(LOGO_SIZE) $(FAVICON_SIZE) --outdir docs/assets $(ARGS) >/dev/null
	@mv docs/assets/teardrop-*-$(LOGO_SIZE).svg docs/assets/logo.svg
	@mv docs/assets/teardrop-*-$(FAVICON_SIZE).svg docs/assets/favicon.svg
	@echo "wrote docs/assets/logo.svg ($(LOGO_SIZE)px, n=$(N) k=$(K) $(STYLE))"
	@echo "wrote docs/assets/favicon.svg ($(FAVICON_SIZE)px, size-optimised)"

# Write docs/assets/scroll.svg, the foliate scrollwork tile wave mode drifts
# behind the page. One seamless 240x120 tile; styles.css repeats it at two
# scales and masks it to --scroll-ink, so the colour lives in the CSS and this
# file is pure geometry. Re-run only if the motif itself changes.
#
#   make scroll
#   make scroll ARGS="--print-uri"           # data URI, if it ever inlines
scroll:
	@python generate_scroll.py --outdir docs/assets $(ARGS)

# ============================================================================
# GROUP 1b -- refresh an Atlas, one step at a time.
# ============================================================================
# Each Atlas owns its pipeline; these are DELEGATIONS, not reimplementations --
# every recipe is `$(MAKE) -C` into that Atlas's own Makefile, so the logic
# lives where it is understood and this file cannot drift from it.
#
# They are deliberately NOT chained. Refreshing a collection is a thing you
# watch, and the expensive steps are hours long, so each runs on its own and
# you decide what comes next. `make steps` prints the order and the costs.
#
# The three pipelines share no stages and no vocabulary. What they share is the
# SHAPE: acquire (networked, hours) -> parse (offline, seconds) -> build
# tree.json -> changelog -> audit. The prefixes below are `ws-`, `ebs-` and
# `sd-` so a step always says which collection it belongs to.
#
# When any Atlas has been rebuilt, come back here and run `make data`.

ATLAS_ROOT ?= ../atlases
WS  := $(ATLAS_ROOT)/sanskrit-wikisource-atlas
EBS := $(ATLAS_ROOT)/e-bharatisampat-atlas
SD  := $(ATLAS_ROOT)/sanskrit-documents-atlas
JQ  := $(ATLAS_ROOT)/jain-quantum-atlas
GR  := $(ATLAS_ROOT)/gretil-atlas

# --- Sanskrit Wikisource ----------------------------------------------------
# The cheap one: a monthly XML dump, so acquisition is one download rather than
# a crawl. No rate limit applies -- we are fetching a file, not walking a site.

# Resolve the latest complete monthly dump and download/verify/decompress
# whatever is missing or stale. No-ops if already current.
#   MINUTES, network, resumable.
ws-dump:
	$(MAKE) -C $(WS) refresh-dump

# The dump -> docs/data/tree.json. Parallel across cores; WORKERS=n to bound it.
#   ~MINUTES, offline.
ws-process:
	$(MAKE) -C $(WS) process $(if $(WORKERS),WORKERS=$(WORKERS))

# Materialize any monthly snapshot the historical range is missing. NOT part of
# `process` -- a new dump gives you a new tree.json while the snapshots, and so
# the growth chart, stay where they were.
#   HOURS from scratch, MINUTES for one new month: expensive content
#   calculations are cached, and months already materialized are reused.
ws-backfill:
	$(MAKE) -C $(WS) backfill

# The materialized snapshots -> docs/data/changelog.json. Needs `ws-backfill`
# to have covered the month you want plotted; on its own it rebuilds from
# whatever is already on disk.
#   UNDER A MINUTE, offline.
ws-changelog:
	$(MAKE) -C $(WS) regen-changelog

# Structural problems on the live wiki, and rewrite the About page's findings.
#   SECONDS, offline.
ws-audit:
	$(MAKE) -C $(WS) audit-update-about

# --- E-bhāratīsampat --------------------------------------------------------
# The expensive one, and the only one needing clearance first.

# Establish session clearance once. Session-lived: when a fetcher reports it
# has lapsed, run this again.
#   INTERACTIVE, seconds. Needed before either fetch step below.
ebs-clearance:
	$(MAKE) -C $(EBS) clearance $(if $(ARGS),ARGS="$(ARGS)")

# The catalogue walk: ~11,066 requests at one per 2s.
#   ~6.5h, network. Ctrl-C stops cleanly and a rerun resumes from the cache,
#   with the progress bar picking up at the cached count.
#   ARGS="--limit 50" for a bounded taste.
ebs-fetch-metadata:
	$(MAKE) -C $(EBS) fetch-metadata $(if $(ARGS),ARGS="$(ARGS)")

# The metadata cache -> published JSON. Prints field coverage, which is the
# tripwire for the site changing its markup.
#   SECONDS, offline.
ebs-parse-metadata:
	$(MAKE) -C $(EBS) parse-metadata

# The text walk. Budget by REQUESTS, not books -- a book is many chapters.
#   HOURS, network, resumable; nothing is ever fetched twice.
#   MAX_REQUESTS=2000 MAX_CHUNKS=20 gets ~83% cheaply.
ebs-fetch-text:
	$(MAKE) -C $(EBS) fetch-text $(if $(MAX_REQUESTS),MAX_REQUESTS=$(MAX_REQUESTS)) \
	    $(if $(MAX_CHUNKS),MAX_CHUNKS=$(MAX_CHUNKS)) $(if $(ARGS),ARGS="$(ARGS)")

# The cached text -> sizes. A pure function of the cache, so it is recomputed
# rather than carried between machines.
#   ~1.5 MIN on 8 cores, offline.
ebs-count-sizes:
	$(MAKE) -C $(EBS) count-sizes

#   ~1s, offline.
ebs-build:
	$(MAKE) -C $(EBS) build

# Monthly, the granularity all three share so this repo can plot one axis.
#   SECONDS, offline.
ebs-changelog:
	$(MAKE) -C $(EBS) changelog

#   SECONDS, offline.
ebs-audit:
	$(MAKE) -C $(EBS) audit-update-about

# --- Sanskrit Documents -----------------------------------------------------
# Two tiers that do not compare anything: tier 1 builds the scrape list, tier 2
# walks it.

# Tier 1: sitemap + 87 topic pages + 20 folder pages -> the scrape list.
#   ~108 requests, MINUTES, network.
sd-fetch-metadata:
	$(MAKE) -C $(SD) fetch-metadata $(if $(ARGS),ARGS="$(ARGS)")

# Rebuild that scrape list from the pages already cached, with NO NETWORK.
# Use this to repair a lost or truncated catalogue.jsonl rather than refetching
# 87 pages that are sitting on disk.
#   ~1s, offline.
sd-build-catalogue:
	$(MAKE) -C $(SD) build-catalogue

# Tier 2: every document in the catalogue, one per 2s.
#   ~9,781 requests, ~5.4h, network. The cache IS the resume state -- a file on
#   disk means done -- so a rerun picks up where it stopped.
sd-fetch-text:
	$(MAKE) -C $(SD) fetch-text $(if $(ARGS),ARGS="$(ARGS)")

# The fetched pages -> inventory.
#   SECONDS, offline.
sd-parse-site:
	$(MAKE) -C $(SD) parse-site

# The cached topic pages -> the topics axis.
#   SECONDS, offline.
sd-parse-listings:
	$(MAKE) -C $(SD) parse-listings-site

#   ~15s, offline.
sd-count-sizes:
	$(MAKE) -C $(SD) count-sizes

# Needs the three steps above; errors telling you which is missing.
#   SECONDS, offline. Also stamps docs/VERSION.
sd-build:
	$(MAKE) -C $(SD) build

#   SECONDS, offline.
sd-changelog:
	$(MAKE) -C $(SD) changelog

# The orphan probe runs by default (~20 HEADs, ~40s) and cannot be switched
# off. It reports INCONCLUSIVE rather than zero when it cannot ask, and leaves
# the published figure standing.
#   ~1 MIN, mostly offline.
sd-audit:
	$(MAKE) -C $(SD) audit-update-about

# --- Jain Quantum -----------------------------------------------------------
# Two catalogues, one text source. The jainelibrary.org API metadata under
# data/metadata_cache/jainelibrary/ came from a one-off pull and has no
# fetcher in rivulet yet; everything below is the jainqq.org side.

# Cloudflare clearance for jainqq.org, earned in a separate visible Chrome.
#   SECONDS, network, session-lived; the fetchers re-earn it when it lapses.
jq-clearance:
	$(MAKE) -C $(JQ) clearance $(if $(ARGS),ARGS="$(ARGS)")

# The 34-page catalog -> data/metadata_cache/jainqq/.
#   ~34 requests, ~1.5 MIN, network.
jq-fetch-catalog:
	$(MAKE) -C $(JQ) fetch-catalog $(if $(ARGS),ARGS="$(ARGS)")

#   SECONDS, offline. Writes catalogue.jsonl and prints the language slices.
jq-parse-catalog:
	$(MAKE) -C $(JQ) parse-catalog

# One booktext JSON per item with text, by language slice.
#   sanskrit-only (default) ~1,974 requests, ~1.2h; any-sanskrit adds ~2,645.
jq-fetch-text:
	$(MAKE) -C $(JQ) fetch-text $(if $(ARGS),ARGS="$(ARGS)")

#   SECONDS, offline. Needs rivulet (the writer); the rules are the Atlas's.
jq-extract-text:
	$(MAKE) -C $(JQ) extract-text

#   ~15 MIN single-threaded for the Sanskrit-only slice; WORKERS=n.
jq-count-sizes:
	$(MAKE) -C $(JQ) count-sizes $(if $(WORKERS),WORKERS=$(WORKERS))

#   SECONDS, offline. Also stamps docs/VERSION.
jq-build:
	$(MAKE) -C $(JQ) build

#   SECONDS, offline.
jq-changelog:
	$(MAKE) -C $(JQ) changelog

# --- GRETIL -----------------------------------------------------------------
# Nothing to acquire: the collection is closed and every copy is on disk under
# GRETIL_ROOT (default ~/Git/gretil). Everything is offline and takes seconds.

gr-inventory:
	$(MAKE) -C $(GR) inventory

gr-count-sizes:
	$(MAKE) -C $(GR) count-sizes

# Needs rivulet (the writer); writes data/text_extract/{legacy,tei}/.
gr-extract-text:
	$(MAKE) -C $(GR) extract-text

gr-build:
	$(MAKE) -C $(GR) build

gr-changelog:
	$(MAKE) -C $(GR) changelog

# --- the map ----------------------------------------------------------------

# What each Atlas holds, and which steps would actually do something. Reads
# only -- no network, no writes. Run this FIRST on a machine you have not
# touched in a while; `make steps` then tells you what each flagged step costs.
#
# Staleness is mtime, so it is advisory in both directions: a touched file
# reads as stale, and a parser change makes every downstream file wrong while
# moving no timestamp at all. The offline steps cost seconds, so re-run rather
# than agonise. A `partial` corpus is the row to actually think about -- that
# is hours of walking, and copying the cache from another machine beats it.
status:
	@python atlas_status.py $(ARGS)

# Print each Atlas's steps, split by what they cost you. Runs nothing.
#
# The split is the point. ACQUIRE hits the network and takes hours; REGENERATE
# reads a cache already on disk and takes seconds. You need the first only when
# you want new data from the site -- everything below it can be re-run freely,
# as often as you like, to rebuild published files from what you already hold.
steps:
	@echo
	@echo "  (\`make status\` first -- it says which of these are actually needed.)"
	@echo
	@echo "  ======================================================================"
	@echo "  ACQUIRE -- hits the network, takes hours, resumable"
	@echo "  ======================================================================"
	@echo "  Only when you want NEW data from the site."
	@echo
	@echo "    Sanskrit Wikisource -- a monthly dump, not a crawl"
	@echo "      make ws-dump              minutes    latest monthly XML dump"
	@echo "      make ws-backfill          minutes*   materialize the new month's snapshot"
	@echo "                                           (* hours only from scratch; cached)"
	@echo
	@echo "    E-bharatisampat -- needs clearance first"
	@echo "      make ebs-clearance        seconds    session-lived; rerun when it lapses"
	@echo "      make ebs-fetch-metadata   ~6.5h      ~11,066 requests"
	@echo "      make ebs-fetch-text       hours      budget by MAX_REQUESTS"
	@echo
	@echo "    Sanskrit Documents -- two tiers, list then walk"
	@echo "      make sd-fetch-metadata    minutes    ~108 requests"
	@echo "      make sd-fetch-text        ~5.4h      ~9,781 requests"
	@echo
	@echo "    Jain Quantum -- needs Cloudflare clearance first"
	@echo "      make jq-clearance         seconds    session-lived; re-earned automatically"
	@echo "      make jq-fetch-catalog     ~1.5min    34 requests"
	@echo "      make jq-fetch-text        ~1.2h      sanskrit-only slice (ARGS=\"--languages any-sanskrit\" adds ~1h40)"
	@echo
	@echo "    GRETIL -- nothing to acquire; every copy is on disk"
	@echo
	@echo "  ======================================================================"
	@echo "  REGENERATE -- offline, from the cache already on disk"
	@echo "  ======================================================================"
	@echo "  Safe to re-run any time. This is what you want after a parser or"
	@echo "  builder change, or to repair a file -- no refetching."
	@echo
	@echo "    Sanskrit Wikisource"
	@echo "      make ws-process           minutes    dump      -> tree.json"
	@echo "      make ws-changelog         <1min      snapshots -> changelog.json"
	@echo "      make ws-audit             seconds              -> about.html"
	@echo
	@echo "    E-bharatisampat"
	@echo "      make ebs-parse-metadata   seconds    cache     -> published JSON"
	@echo "      make ebs-count-sizes      ~1.5min    cache     -> text_sizes.jsonl"
	@echo "      make ebs-build            ~1s                  -> tree.json"
	@echo "      make ebs-changelog        seconds              -> changelog.json"
	@echo "      make ebs-audit            seconds              -> about.html"
	@echo
	@echo "    Sanskrit Documents"
	@echo "      make sd-build-catalogue   ~1s        cache     -> catalogue.jsonl"
	@echo "      make sd-parse-site        seconds    cache     -> site_inventory"
	@echo "      make sd-parse-listings    seconds    cache     -> site_listings"
	@echo "      make sd-count-sizes       ~15s       cache     -> site_sizes"
	@echo "      make sd-build             seconds              -> tree.json, VERSION"
	@echo "      make sd-changelog         seconds              -> changelog.json"
	@echo "      make sd-audit             ~1min      *         -> about.html"
	@echo
	@echo "    Jain Quantum"
	@echo "      make jq-parse-catalog     seconds    cache     -> catalogue.jsonl"
	@echo "      make jq-extract-text      seconds    cache     -> text_extract/ (rivulet)"
	@echo "      make jq-count-sizes       ~15min     cache     -> sizes.jsonl (WORKERS=n)"
	@echo "      make jq-build             seconds              -> tree.json, VERSION"
	@echo "      make jq-changelog         seconds              -> changelog.json"
	@echo
	@echo "    GRETIL"
	@echo "      make gr-inventory         seconds    checkouts -> inventory.jsonl"
	@echo "      make gr-count-sizes       seconds              -> sizes.jsonl"
	@echo "      make gr-extract-text      seconds              -> text_extract/ (rivulet)"
	@echo "      make gr-build             seconds              -> tree.json, VERSION"
	@echo "      make gr-changelog         seconds              -> changelog.json"
	@echo
	@echo "    Then here, once any Atlas has rebuilt:"
	@echo "      make data                 seconds              counts+growth+search"
	@echo
	@echo "  * sd-audit runs a ~40s orphan probe. It reports INCONCLUSIVE"
	@echo "    rather than zero when it cannot ask, and leaves the published"
	@echo "    figure standing."
	@echo
	@echo "  A FULL REFRESH is one column then the other, top to bottom, per"
	@echo "  Atlas. Acquisition is resumable -- Ctrl-C stops cleanly and a rerun"
	@echo "  picks up from the cache -- so it is safe to do it in sittings."
	@echo

# ============================================================================
# GROUP 2 -- serve the site.
# ============================================================================

# Serve docs/ locally on port 8000, gzipping JSON/JS/HTML/CSS. The Atlases use
# 8001-8003, so all four can run side by side.
#
# **This IS the published site.** What you see here is what GitHub Pages
# serves, byte for byte -- no local-only affordances, no probing. If it looks
# different deployed, that is a bug.
serve:
	cd docs && python ../serve_docs.py

# The separate mode: adds `txt` links into the Atlases' locally served corpus
# text. LOCALHOST ONLY, and deliberately NOT what the published site shows.
# Each Atlas must also be running with its own --fulltext for its rows to link
# -- see `make serve-all-fulltext`, which starts all four correctly.
serve-fulltext:
	cd docs && python ../serve_docs.py --fulltext $(ARGS)

free-server-port:
	kill $$(lsof -ti tcp:8000)

# Serve all four in the background, on the ports docs/local-links.js assumes,
# so a local home page links to the local Atlases. Logs to
# /tmp/sagara-serve-<port>.log; a port already in use is left alone.
#   make serve-all
#   make free-all-server-ports               # stop them again
ATLAS_ROOT ?= ../atlases
SERVE_ALL_PORTS := 8000 8001 8002 8003 8004 8005

serve-all:
	@$(MAKE) --no-print-directory serve-one PORT=8000 DIR=.
	@$(MAKE) --no-print-directory serve-one PORT=8001 DIR=$(ATLAS_ROOT)/sanskrit-wikisource-atlas
	@$(MAKE) --no-print-directory serve-one PORT=8002 DIR=$(ATLAS_ROOT)/e-bharatisampat-atlas
	@$(MAKE) --no-print-directory serve-one PORT=8003 DIR=$(ATLAS_ROOT)/sanskrit-documents-atlas
	@$(MAKE) --no-print-directory serve-one PORT=8004 DIR=$(ATLAS_ROOT)/jain-quantum-atlas
	@$(MAKE) --no-print-directory serve-one PORT=8005 DIR=$(ATLAS_ROOT)/gretil-atlas
	@echo
	@echo "  Sagarasangama         http://localhost:8000"
	@echo "  sanskrit-wikisource   http://localhost:8001"
	@echo "  e-bharatisampat       http://localhost:8002"
	@echo "  sanskrit-documents    http://localhost:8003"
	@echo "  jain-quantum          http://localhost:8004"
	@echo "  gretil                http://localhost:8005"
	@echo
	@echo "logs /tmp/sagara-serve-<port>.log -- stop with: make free-all-server-ports"

# All four in FULLTEXT mode: every server gets --fulltext, so each Atlas serves
# its own corpus text and the parent offers `txt` links into it.
#
# LOCALHOST ONLY. Every one of these binds 127.0.0.1 rather than all
# interfaces, so unlike `serve-all` this is not reachable from your phone --
# that is the point. The text is not ours to hand out.
#   make serve-all-fulltext
#   make free-all-server-ports               # stop them again
serve-all-fulltext:
	@$(MAKE) --no-print-directory serve-one PORT=8000 DIR=. SERVE_ARGS=--fulltext
	@$(MAKE) --no-print-directory serve-one PORT=8001 DIR=$(ATLAS_ROOT)/sanskrit-wikisource-atlas SERVE_ARGS=--fulltext
	@$(MAKE) --no-print-directory serve-one PORT=8002 DIR=$(ATLAS_ROOT)/e-bharatisampat-atlas SERVE_ARGS=--fulltext
	@$(MAKE) --no-print-directory serve-one PORT=8003 DIR=$(ATLAS_ROOT)/sanskrit-documents-atlas SERVE_ARGS=--fulltext
	@$(MAKE) --no-print-directory serve-one PORT=8004 DIR=$(ATLAS_ROOT)/jain-quantum-atlas SERVE_ARGS=--fulltext
	@$(MAKE) --no-print-directory serve-one PORT=8005 DIR=$(ATLAS_ROOT)/gretil-atlas SERVE_ARGS=--fulltext
	@echo
	@echo "  FULLTEXT MODE -- localhost only, NOT what the published site shows."
	@echo
	@echo "  Sagarasangama         http://localhost:8000"
	@echo "  sanskrit-wikisource   http://localhost:8001"
	@echo "  e-bharatisampat       http://localhost:8002"
	@echo "  sanskrit-documents    http://localhost:8003"
	@echo
	@echo "logs /tmp/sagara-serve-<port>.log -- stop with: make free-all-server-ports"

# One backgrounded server; serve-all sets PORT and DIR. Runs from DIR/docs the
# way each repo's own `serve` does, so relative data paths resolve alike.
# SERVE_ARGS is empty for serve-all and --fulltext for serve-all-fulltext.
serve-one:
	@if lsof -ti tcp:$(PORT) >/dev/null 2>&1; then \
	    echo "port $(PORT) already in use, left alone ($(DIR))"; \
	elif [ ! -f "$(DIR)/serve_docs.py" ]; then \
	    echo "no serve_docs.py under $(DIR), skipped port $(PORT)"; \
	else \
	    ( cd "$(DIR)/docs" && nohup python ../serve_docs.py $(PORT) $(SERVE_ARGS) \
	        > /tmp/sagara-serve-$(PORT).log 2>&1 & echo "started $(DIR) on port $(PORT)$(if $(SERVE_ARGS), [fulltext]) (pid $$!)" ); \
	fi

# Stop whatever is on the four ports, including servers started by hand.
free-all-server-ports:
	@for p in $(SERVE_ALL_PORTS); do \
	    pid=$$(lsof -ti tcp:$$p 2>/dev/null); \
	    if [ -n "$$pid" ]; then kill $$pid && echo "freed port $$p (pid $$pid)"; \
	    else echo "port $$p already free"; fi; \
	done

get-server-ip-address:
	ifconfig | grep "inet " | grep -v 127.0.0.1
