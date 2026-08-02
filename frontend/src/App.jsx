import React, { useState, useEffect, useCallback } from 'react';
import { ENTITY_META, TYPE_ORDER, colorOf, colorAlpha, buildSpans } from './data.js';
import { createExtraction, getExtraction, triggerExtraction, listExtractions } from './api/extractions.js';
import { pollUntil } from './api/poll.js';
import Spinner from './components/Spinner.jsx';
import Header from './components/Header.jsx';
import Sidebar from './components/Sidebar.jsx';
import UploadZone from './components/UploadZone.jsx';
import DocumentPanel from './components/DocumentPanel.jsx';
import EntityLegend from './components/EntityLegend.jsx';
import HoverTooltip from './components/HoverTooltip.jsx';

const freshFilters = () => ({ monetary: true, percentage: true, date: true, duration: true, other_number: true });

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [history, setHistory] = useState([]);
  const [currentId, setCurrentId] = useState(null);
  const [stage, setStage] = useState('upload'); // upload | parsingDoc | parsed | loading | results | errorParse | errorExtract
  const [fileName, setFileName] = useState('');
  const [documentText, setDocumentText] = useState('');
  const [activeFilters, setActiveFilters] = useState(freshFilters());
  const [hover, setHover] = useState(null);
  const [entities, setEntities] = useState([]);
  const [elapsedLabel, setElapsedLabel] = useState('');

  const refreshHistory = useCallback(async () => {
    try {
      setHistory(await listExtractions());
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { refreshHistory(); }, [refreshHistory]);

  const handleFiles = async (fileList) => {
    const file = fileList && fileList[0];
    if (!file) return;
    setFileName(file.name);
    setStage('parsingDoc');
    setCurrentId(null);
    setEntities([]);
    setDocumentText('');
    setElapsedLabel('');
    setHover(null);
    setActiveFilters(freshFilters());
    try {
      const created = await createExtraction(file);
      setCurrentId(created.id);
      await refreshHistory();
      const result = await pollUntil({
        fn: () => getExtraction(created.id),
        isDone: (r) => r.stage !== 'parsingDoc',
      });
      await refreshHistory();
      if (result.stage === 'parsed') {
        setDocumentText(result.parsedText);
        setStage('parsed');
      } else {
        setStage('errorParse');
      }
    } catch (err) {
      console.error(err);
      setStage('errorParse');
    }
  };

  const onExtract = async () => {
    if (!currentId) return;
    setStage('loading');
    try {
      await triggerExtraction(currentId);
      await refreshHistory();
      const result = await pollUntil({
        fn: () => getExtraction(currentId),
        isDone: (r) => r.stage !== 'loading',
      });
      await refreshHistory();
      if (result.stage === 'results') {
        setEntities(result.entities);
        setElapsedLabel(result.elapsedLabel);
        setStage('results');
      } else {
        setStage('errorExtract');
      }
    } catch (err) {
      console.error(err);
      setStage('errorExtract');
    }
  };

  const onNewExtraction = () => {
    setStage('upload'); setFileName(''); setCurrentId(null); setEntities([]);
    setDocumentText(''); setHover(null); setActiveFilters(freshFilters());
  };

  const onSelectHistory = async (id) => {
    try {
      const detail = await getExtraction(id);
      setCurrentId(id);
      setStage(detail.stage);
      setFileName(detail.fileName);
      setDocumentText(detail.parsedText);
      setEntities(detail.entities);
      setElapsedLabel(detail.elapsedLabel);
      setHover(null);
      setActiveFilters(freshFilters());
    } catch (err) { console.error(err); }
  };

  const toggleFilter = (type) => setActiveFilters((f) => ({ ...f, [type]: !f[type] }));

  const isUpload = stage === 'upload';
  const isParsingDoc = stage === 'parsingDoc';
  const isParsed = stage === 'parsed';
  const isLoading = stage === 'loading';
  const isResults = stage === 'results';
  const isErrorParse = stage === 'errorParse';
  const isErrorExtract = stage === 'errorExtract';
  const isCommitted = !isUpload && !isParsingDoc;
  const showTextPanel = isCommitted && !isErrorParse;
  const isResultsSuccess = isResults && entities.length > 0;
  const showNoEntitiesNotice = isResults && entities.length === 0;
  const hasLegend = isResults && entities.length > 0;
  const showRightPanel = isResults;

  const wordCount = documentText.trim() ? documentText.trim().split(/\s+/).length : 0;
  const fileMeta = `1 page · ${wordCount} words · 6.1 KB`;

  const rawSpans = buildSpans(documentText, isResults ? entities : []);
  const displaySpans = rawSpans.map((seg) => {
    if (!seg.isEntity) return seg;
    const active = activeFilters[seg.type];
    const style = active
      ? { background: colorAlpha(seg.type, 0.22), borderBottom: `2px solid ${colorOf(seg.type)}`, borderRadius: '2px', padding: '0 1px', cursor: 'pointer' }
      : { background: 'transparent', borderBottom: '1px dashed oklch(0.45 0.01 258)', color: 'oklch(0.5 0.01 258)', cursor: 'default' };
    return { ...seg, style, active };
  });

  const counts = {};
  entities.forEach((e) => { counts[e.type] = (counts[e.type] || 0) + 1; });
  const legendItems = TYPE_ORDER.filter((t) => counts[t]).map((t) => ({
    type: t, label: ENTITY_META[t].label, count: counts[t], active: activeFilters[t],
  }));

  return (
    <div className="font-sans bg-surface text-ink h-screen flex flex-col overflow-hidden">
      <Header />

      <div className="flex-1 min-h-0 flex">
        <Sidebar
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
          history={history}
          currentId={currentId}
          onNewExtraction={onNewExtraction}
          onSelectHistory={onSelectHistory}
        />

        {/* Middle panel */}
        <div className="flex-1 min-w-0 flex flex-col">
          {isUpload && (
            <UploadZone onFiles={handleFiles} />
          )}

          {isParsingDoc && (
            <div className="flex-1 flex flex-col items-center justify-center gap-4">
              <Spinner />
              <div className="text-[13px] text-ink-muted font-mono">Parsing document…</div>
            </div>
          )}

          {isCommitted && (
            <DocumentPanel
              fileName={fileName}
              fileMeta={fileMeta}
              isParsed={isParsed}
              isLoading={isLoading}
              isResultsSuccess={isResultsSuccess}
              entitiesCount={entities.length}
              elapsedLabel={elapsedLabel}
              isErrorParse={isErrorParse}
              isErrorExtract={isErrorExtract}
              onExtract={onExtract}
              onNewExtraction={onNewExtraction}
              showTextPanel={showTextPanel}
              showNoEntitiesNotice={showNoEntitiesNotice}
              displaySpans={displaySpans}
              setHover={setHover}
            />
          )}
        </div>

        {showRightPanel && (
          <EntityLegend hasLegend={hasLegend} legendItems={legendItems} onToggleFilter={toggleFilter} />
        )}
      </div>

      <HoverTooltip hover={hover} />
    </div>
  );
}
