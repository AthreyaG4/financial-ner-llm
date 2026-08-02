import { useRef } from 'react';

export default function UploadZone({ onFiles }) {
  const fileInputRef = useRef(null);

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-10">
      <div className="w-full max-w-[560px]">
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); onFiles(e.dataTransfer.files); }}
          onClick={() => fileInputRef.current && fileInputRef.current.click()}
          className="cursor-pointer border-[1.5px] border-dashed border-white/18 rounded-xl px-8 py-14 text-center bg-[oklch(0.2_0.013_258_/_0.5)]"
        >
          <div className="w-16 h-16 rounded-full bg-[oklch(0.62_0.16_252_/_0.16)] flex items-center justify-center mx-auto mb-[22px]">
            <div className="flex flex-col items-center">
              <div className="w-0 h-0 border-l-8 border-l-transparent border-r-8 border-r-transparent border-b-[11px] border-b-accent-light" />
              <div className="w-1 h-[18px] bg-accent-light rounded-sm -mt-px" />
            </div>
          </div>
          <div className="text-[17px] font-semibold mb-1.5">Drop a financial document to begin</div>
          <div className="text-[13px] text-ink-muted mb-4.5">PDF format · invoices, statements, filings</div>
          <div className="inline-flex items-center gap-2 px-[18px] py-[9px] rounded-[7px] bg-accent text-accent-ink text-[13px] font-semibold">Browse files</div>
          <input ref={fileInputRef} type="file" accept="application/pdf" onChange={(e) => onFiles(e.target.files)} className="hidden" />
        </div>
      </div>
    </div>
  );
}
